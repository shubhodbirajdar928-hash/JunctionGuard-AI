"""
Explainable Junction Risk Score Engine for JunctionGuard AI.
Combines:
  1. Track A: Real-time Traffic Indicators (Density, Speed, Conflicts, Pedestrian Activity)
  2. Track B: Historical Accident Severity Score (0-100 scale from cleaned Kaggle dataset)
  3. Citizen Hazard Reports: User-submitted issue counts & severities (from data/citizen_reports/)

Features a transparent, interpretable weighted scoring algorithm with explainable factor weight outputs:
  [{"factor": "Historical Accident Severity", "weight": 0.30}, ...]
where weights sum to 1.0.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union

from src.analytics.data_loader import compute_historical_risk_score, DATA_DIR
from src.database import fetch_citizen_reports, update_junction_risk

CITIZEN_REPORTS_JSON = os.path.join(DATA_DIR, "citizen_reports", "reports.json")

# Standard Baseline Component Weights (Sum = 1.0)
DEFAULT_WEIGHTS = {
    "historical_accidents": 0.30,      # Track B1: Kaggle Accident Severity & Frequency
    "traffic_density": 0.20,           # Track A2: Vehicle Density & Flow Velocity
    "near_miss_conflicts": 0.20,       # Track A2: Spatial Conflict Proximity Index
    "pedestrian_activity": 0.15,       # Track A2: Pedestrian Crossing & Vulnerability
    "citizen_reports": 0.15            # Citizen Feedback: Hazard Submissions & Clustering
}

def parse_report_timestamp(ts_val: Any) -> Optional[datetime]:
    """Parses various timestamp representations into a Python datetime object."""
    if not ts_val:
        return None
    if isinstance(ts_val, datetime):
        return ts_val
    ts_str = str(ts_val).strip()
    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d"
    ]:
        try:
            return datetime.strptime(ts_str[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        pass
    return None

def classify_report_media(r: Dict[str, Any]) -> str:
    """Classifies a report as 'video', 'photo', or 'text' based on media attributes."""
    media_type = str(r.get("media_type") or "").lower()
    media_url = str(r.get("media_url") or "").lower()
    media_fn = str(r.get("media_filename") or "").lower()
    media_rel = str(r.get("media_relative_path") or "").lower()

    # Video check: 3 points
    video_exts = (".mp4", ".mov", ".avi", ".webm", ".mkv")
    if "video" in media_type or any(ext in media_url or ext in media_fn or ext in media_rel for ext in video_exts):
        return "video"

    # Photo check: 2 points
    image_exts = (".jpg", ".jpeg", ".png", ".webp", ".gif")
    if "image" in media_type or "photo" in media_type or any(ext in media_url or ext in media_fn or ext in media_rel for ext in image_exts):
        return "photo"
    if r.get("media_url") and str(r.get("media_url")).strip() not in ["", "None", "null"]:
        return "photo"
    if r.get("media_filename") and str(r.get("media_filename")).strip() not in ["", "None", "null"]:
        return "photo"

    return "text"

def _resolve_duplicate_cluster(cluster_items: List[Tuple[datetime, Dict[str, Any]]]) -> Dict[str, Any]:
    """Given multiple duplicate reports from the same reporter, retain the report with the highest evidence tier."""
    if len(cluster_items) == 1:
        return cluster_items[0][1]
    points_map = {"video": 3, "photo": 2, "text": 1}
    best_rep = cluster_items[0][1]
    best_pts = points_map.get(classify_report_media(best_rep), 1)

    for _, r in cluster_items[1:]:
        pts = points_map.get(classify_report_media(r), 1)
        if pts > best_pts:
            best_rep = r
            best_pts = pts
    return best_rep

def compute_citizen_report_cluster(
    reports: List[Dict[str, Any]],
    window_days: int = 30,
    dedupe_window_minutes: int = 10,
    reference_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Evaluates citizen report clustering for a junction:
      1. Filters reports within a rolling time window (e.g. last 30 days).
      2. Anti-abuse: Deduplicates reports from same reporter_name within 10 minutes.
         Note: A production version would need proper user accounts/auth for this, not just a name field.
      3. Weights reports: Text-only = 1 pt, Photo = 2 pts, Video = 3 pts.
      4. Sums into report_severity_score and normalizes to 0-100 scale (capped at 10+ points = 100).
    """
    now = reference_time or datetime.now()
    cutoff = now - timedelta(days=window_days)

    if not reports:
        return {
            "cluster_size": 0,
            "media_count": 0,
            "photo_count": 0,
            "video_count": 0,
            "text_count": 0,
            "report_severity_score": 0,
            "normalized_score": 0.0,
            "summary_line": "0 reports in last 30 days, 0 with photo/video evidence",
            "deduplicated_reports": []
        }

    # Step 1: Filter to 30-day window and parse timestamps
    recent_reports: List[Tuple[datetime, Dict[str, Any]]] = []
    for r in reports:
        raw_ts = r.get("timestamp") or r.get("submitted_at")
        ts = parse_report_timestamp(raw_ts)
        if ts is None:
            ts = now
        if ts >= cutoff:
            recent_reports.append((ts, r))

    if not recent_reports:
        return {
            "cluster_size": 0,
            "media_count": 0,
            "photo_count": 0,
            "video_count": 0,
            "text_count": 0,
            "report_severity_score": 0,
            "normalized_score": 0.0,
            "summary_line": "0 reports in last 30 days, 0 with photo/video evidence",
            "deduplicated_reports": []
        }

    # Step 2: Anti-abuse deduplication
    # Anti-abuse deduplication: In hackathon-scope, we deduplicate by reporter_name within a 10-minute window.
    # Note: A production version would need proper user accounts/auth for this, not just a name field.
    grouped_by_reporter: Dict[str, List[Tuple[datetime, Dict[str, Any]]]] = {}
    for ts, r in recent_reports:
        rep_name = str(r.get("reporter_name") or "anonymous").strip().lower()
        if rep_name not in grouped_by_reporter:
            grouped_by_reporter[rep_name] = []
        grouped_by_reporter[rep_name].append((ts, r))

    deduplicated: List[Dict[str, Any]] = []
    for rep_name, rep_list in grouped_by_reporter.items():
        rep_list.sort(key=lambda x: x[0])
        current_cluster: List[Tuple[datetime, Dict[str, Any]]] = []

        for ts, r in rep_list:
            if not current_cluster:
                current_cluster.append((ts, r))
            else:
                last_ts = current_cluster[-1][0]
                diff_secs = abs((ts - last_ts).total_seconds())
                if diff_secs <= dedupe_window_minutes * 60:
                    current_cluster.append((ts, r))
                else:
                    deduplicated.append(_resolve_duplicate_cluster(current_cluster))
                    current_cluster = [(ts, r)]
        if current_cluster:
            deduplicated.append(_resolve_duplicate_cluster(current_cluster))

    # Step 3: Weight reports
    points_map = {"video": 3, "photo": 2, "text": 1}
    photo_count = 0
    video_count = 0
    text_count = 0
    total_points = 0

    for rep in deduplicated:
        m_tier = classify_report_media(rep)
        pts = points_map[m_tier]
        total_points += pts
        if m_tier == "video":
            video_count += 1
        elif m_tier == "photo":
            photo_count += 1
        else:
            text_count += 1

    cluster_size = len(deduplicated)
    media_count = photo_count + video_count

    # Step 4: Normalize to 0-100 scale using reasonable cap (10+ weighted points = 100)
    normalized_score = round(min(100.0, (total_points / 10.0) * 100.0), 1)

    summary_line = (
        f"{cluster_size} {'report' if cluster_size == 1 else 'reports'} in last 30 days, "
        f"{media_count} with photo/video evidence"
    )

    return {
        "cluster_size": cluster_size,
        "media_count": media_count,
        "photo_count": photo_count,
        "video_count": video_count,
        "text_count": text_count,
        "report_severity_score": total_points,
        "normalized_score": normalized_score,
        "summary_line": summary_line,
        "deduplicated_reports": deduplicated
    }

def load_citizen_reports_data(junction_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Loads citizen reports from SQLite database and data/citizen_reports/reports.json.
    Filters by junction_id if provided.
    """
    reports: List[Dict[str, Any]] = []

    # 1. Load from SQLite Database
    try:
        db_reports = fetch_citizen_reports(junction_id)
        if db_reports:
            reports.extend(db_reports)
    except Exception:
        pass

    # 2. Load from JSON file if available
    if os.path.exists(CITIZEN_REPORTS_JSON):
        try:
            with open(CITIZEN_REPORTS_JSON, "r", encoding="utf-8") as f:
                json_reports = json.load(f)
                if isinstance(json_reports, list):
                    reports.extend(json_reports)
        except Exception:
            pass

    # Deduplicate by report_id
    seen_ids = set()
    deduped: List[Dict[str, Any]] = []
    for r in reports:
        r_id = r.get("report_id") or r.get("id")
        if r_id:
            if r_id in seen_ids:
                continue
            seen_ids.add(r_id)
        deduped.append(r)

    # Filter by junction_id if specified
    if junction_id is not None:
        filtered = [
            r for r in deduped 
            if str(r.get("junction_id", "")).strip().upper() == str(junction_id).strip().upper()
            or str(r.get("junction_name", "")).strip().lower() in str(junction_id).strip().lower()
        ]
        return filtered

    return deduped

def get_citizen_cluster_stats(
    junction_id: str,
    window_days: int = 30,
    dedupe_window_minutes: int = 10
) -> Dict[str, Any]:
    """
    Retrieves citizen reports for a junction and computes its clustering metrics:
    cluster_size, media_count, photo_count, video_count, normalized_score, summary_line.
    """
    reports = load_citizen_reports_data(junction_id)
    return compute_citizen_report_cluster(
        reports,
        window_days=window_days,
        dedupe_window_minutes=dedupe_window_minutes
    )

def calculate_junction_risk_score(
    traffic_indicators: Optional[Union[Dict[str, Any], float]] = None,
    accident_history_score: float = 40.0,
    citizen_reports: Optional[Union[List[Dict[str, Any]], int, float]] = None,
    weather_condition: str = "Clear",
    is_night: bool = False,
    custom_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Standalone interpretable scoring function combining Track A (Traffic Indicators),
    Track B (Accident History Score), and Citizen Hazard Reports into a 0-100 score.

    Parameters:
    -----------
    traffic_indicators : dict or float
        Track A2 output metrics dict containing:
          - 'traffic_density': float (avg vehicle count per frame, 0-40+)
          - 'speed_proxy': float (avg movement displacement speed, 0-100+)
          - 'conflict_proxy': int (near-miss count, 0-50+)
          - 'pedestrian_activity': float (avg pedestrian count, 0-15+)
          - 'two_wheeler_share_pct': float (0-100%)
        Or a raw 0-100 vision score float.
    accident_history_score : float
        Track B1 output: Normalized 0-100 accident history severity index.
    citizen_reports : list or int or float
        List of citizen report dicts or count of active hazard submissions.
    weather_condition : str
        'Clear', 'Heavy Rain', 'Fog / Mist', 'Monsoon Pour'
    is_night : bool
        Whether ambient lighting is nighttime.
    custom_weights : dict, optional
        Custom factor weights (must sum to 1.0).

    Returns:
    --------
    dict containing:
      - 'risk_score': float (0.0 to 100.0)
      - 'risk_level': str ('LOW', 'MEDIUM', 'HIGH')
      - 'contributing_factors': List[Dict[str, float]] exact format:
            [{"factor": "Historical Accident Severity", "weight": 0.32}, ...] (sum = 1.0)
      - 'component_scores': Dict[str, float] (0-100 sub-scores)
    """
    weights = custom_weights or DEFAULT_WEIGHTS.copy()

    # 1. Normalize Accident History Score (0-100 scale)
    s_hist = max(0.0, min(100.0, float(accident_history_score)))

    # 2. Extract & Normalize Track A Traffic Indicators
    if isinstance(traffic_indicators, dict):
        dens = float(traffic_indicators.get("traffic_density", 12.0))
        spd = float(traffic_indicators.get("speed_proxy", 25.0))
        conflicts = float(traffic_indicators.get("conflict_proxy", 2))
        peds = float(traffic_indicators.get("pedestrian_activity", 2.0))
        two_w_share = float(traffic_indicators.get("two_wheeler_share_pct", 45.0))

        # Traffic Flow Subscore (Density 65% + Speed 35%)
        dens_norm = min(100.0, (dens / 30.0) * 100.0)
        spd_norm = min(100.0, (spd / 60.0) * 100.0)
        two_w_factor = 1.0 + (max(0.0, two_w_share - 40.0) / 150.0)
        s_traffic = min(100.0, ((dens_norm * 0.65) + (spd_norm * 0.35)) * two_w_factor)

        # Conflict / Near-Miss Subscore
        s_conflict = min(100.0, conflicts * 14.0)

        # Pedestrian Activity & Vulnerability Subscore
        s_ped = min(100.0, peds * 20.0)
    elif isinstance(traffic_indicators, (int, float)):
        # If single numeric score provided
        vis_val = float(traffic_indicators)
        s_traffic = max(0.0, min(100.0, vis_val * 0.95))
        s_conflict = max(0.0, min(100.0, vis_val * 1.05))
        s_ped = max(0.0, min(100.0, vis_val * 0.85))
    else:
        # Default baseline for Indian urban intersections
        s_traffic = 55.0
        s_conflict = 45.0
        s_ped = 40.0

    # 3. Extract & Normalize Citizen Reports Clustering Score
    cluster_metrics = None
    if isinstance(citizen_reports, list):
        cluster_metrics = compute_citizen_report_cluster(citizen_reports)
        s_citizen = cluster_metrics["normalized_score"]
    elif isinstance(citizen_reports, (int, float)):
        # If integer count provided (e.g. legacy/mock callers)
        report_count = int(citizen_reports)
        s_citizen = min(100.0, (report_count / 10.0) * 100.0) if report_count > 0 else 0.0
    else:
        s_citizen = 0.0

    # Environmental weather modifier (applied as soft boost during monsoon/rain)
    weather_multiplier = 1.0
    if weather_condition in ["Heavy Rain", "Monsoon Pour"]:
        weather_multiplier += 0.12
    elif weather_condition in ["Fog / Mist"]:
        weather_multiplier += 0.08
    if is_night:
        weather_multiplier += 0.06

    # 4. Compute Weighted Composite Score (Interpretable Weighted Sum)
    w_hist = weights.get("historical_accidents", 0.30)
    w_traf = weights.get("traffic_density", 0.20)
    w_conf = weights.get("near_miss_conflicts", 0.20)
    w_ped = weights.get("pedestrian_activity", 0.15)
    w_cit = weights.get("citizen_reports", weights.get("citizen_hazard_reports", 0.15))

    c_hist = s_hist * w_hist
    c_traf = s_traffic * w_traf
    c_conf = s_conflict * w_conf
    c_ped = s_ped * w_ped
    c_cit = s_citizen * w_cit

    raw_total = (c_hist + c_traf + c_conf + c_ped + c_cit) * weather_multiplier
    total_risk = round(max(0.0, min(100.0, raw_total)), 1)

    # 5. Compute Normalized Explainable Factor Weights (Exact Format, Sum = 1.0)
    contributions = [
        ("Historical Accident Severity", c_hist),
        ("Near-Miss & Spatial Conflicts", c_conf),
        ("Traffic Density & Movement", c_traf),
        ("Pedestrian Activity", c_ped),
        ("Citizen Reports", c_cit)
    ]

    total_contrib = max(0.001, sum(c[1] for c in contributions))
    
    raw_weights = [round(c[1] / total_contrib, 2) for c in contributions]
    
    # Ensure exact sum to 1.00 to avoid float rounding discrepancies
    diff = round(1.0 - sum(raw_weights), 2)
    raw_weights[0] = round(raw_weights[0] + diff, 2)

    contributing_factors = [
        {"factor": contributions[i][0], "weight": float(raw_weights[i])}
        for i in range(len(contributions))
    ]

    # Sort descending by contribution weight for instant explainability
    contributing_factors.sort(key=lambda x: x["weight"], reverse=True)

    # Determine qualitative risk level
    if total_risk >= 70.0:
        risk_level = "HIGH"
    elif total_risk >= 40.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    res_dict = {
        "risk_score": total_risk,
        "risk_level": risk_level,
        "contributing_factors": contributing_factors,
        "component_scores": {
            "historical_accidents": round(s_hist, 1),
            "traffic_density": round(s_traffic, 1),
            "near_miss_conflicts": round(s_conflict, 1),
            "pedestrian_activity": round(s_ped, 1),
            "citizen_reports": round(s_citizen, 1),
            "citizen_hazard_reports": round(s_citizen, 1)
        }
    }
    if cluster_metrics:
        res_dict["cluster_metrics"] = cluster_metrics
    return res_dict

class ExplainableRiskEngine:
    """
    Object-oriented risk calculation engine for JunctionGuard AI.
    Loads junction data, queries indicators and historical scores,
    and updates database records.
    """
    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        self.weights = custom_weights or DEFAULT_WEIGHTS.copy()

    def compute_junction_risk(
        self,
        junction_id: str,
        vision_indicators: Optional[Union[Dict[str, Any], float]] = None,
        vision_risk_score: Optional[float] = None,
        weather_condition: str = "Clear",
        is_night: bool = False
    ) -> Dict[str, Any]:
        """
        Computes composite explainable risk score for a specific junction.
        Automatically loads historical accident score and citizen reports.
        """
        # 1. Load Historical Accident Severity Score (Track B1)
        hist_score, hist_metrics = compute_historical_risk_score(junction_id)

        # 2. Extract Vision / Traffic Indicators (Track A2)
        traffic_input = vision_indicators if vision_indicators is not None else (vision_risk_score or 65.0)

        # 3. Load Citizen Hazard Reports
        reports = load_citizen_reports_data(junction_id)

        # 4. Calculate Risk Score using standalone weighted function
        result = calculate_junction_risk_score(
            traffic_indicators=traffic_input,
            accident_history_score=hist_score,
            citizen_reports=reports,
            weather_condition=weather_condition,
            is_night=is_night,
            custom_weights=self.weights
        )

        # 5. Persist updated score to SQLite and Supabase
        try:
            update_junction_risk(
                junction_id,
                result["risk_score"],
                result["contributing_factors"],
                component_scores=result.get("component_scores")
            )
        except Exception as e:
            print(f"[RiskEngine DB Note] {e}")

        result["junction_id"] = junction_id
        result["hist_metrics"] = hist_metrics
        return result
