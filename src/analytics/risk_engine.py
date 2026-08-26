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
    "citizen_hazard_reports": 0.15     # Citizen Feedback: Hazard Submissions & Severity
}

def load_citizen_reports_data(junction_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Loads citizen reports from data/citizen_reports/reports.json and SQLite database.
    Filters by junction_id if provided.
    """
    reports: List[Dict[str, Any]] = []

    # 1. Load from JSON file if available
    if os.path.exists(CITIZEN_REPORTS_JSON):
        try:
            with open(CITIZEN_REPORTS_JSON, "r", encoding="utf-8") as f:
                json_reports = json.load(f)
                if isinstance(json_reports, list):
                    reports.extend(json_reports)
        except Exception:
            pass

    # 2. Load from SQLite Database
    try:
        db_reports = fetch_citizen_reports(junction_id)
        if db_reports:
            reports.extend(db_reports)
    except Exception:
        pass

    # Filter by junction_id if specified
    if junction_id is not None:
        filtered = [
            r for r in reports 
            if str(r.get("junction_id", "")).strip().upper() == str(junction_id).strip().upper()
            or str(r.get("junction_name", "")).strip().lower() in str(junction_id).strip().lower()
        ]
        return filtered

    return reports

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

    # 3. Extract & Normalize Citizen Hazard Reports Score
    if isinstance(citizen_reports, list):
        report_count = len(citizen_reports)
        if report_count > 0:
            avg_sev = sum(float(r.get("severity", 3)) for r in citizen_reports) / report_count
            s_citizen = min(100.0, (report_count * 15.0) + (avg_sev * 8.0))
        else:
            s_citizen = 30.0  # Baseline when no specific reports filed
    elif isinstance(citizen_reports, (int, float)):
        report_count = int(citizen_reports)
        s_citizen = min(100.0, 30.0 + (report_count * 14.0))
    else:
        report_count = 0
        s_citizen = 35.0

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
    w_cit = weights.get("citizen_hazard_reports", 0.15)

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
        ("Citizen Hazard Reports", c_cit)
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

    return {
        "risk_score": total_risk,
        "risk_level": risk_level,
        "contributing_factors": contributing_factors,
        "component_scores": {
            "historical_accidents": round(s_hist, 1),
            "traffic_density": round(s_traffic, 1),
            "near_miss_conflicts": round(s_conflict, 1),
            "pedestrian_activity": round(s_ped, 1),
            "citizen_hazard_reports": round(s_citizen, 1)
        }
    }

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
            update_junction_risk(junction_id, result["risk_score"], result["contributing_factors"])
        except Exception as e:
            print(f"[RiskEngine DB Note] {e}")

        result["junction_id"] = junction_id
        result["hist_metrics"] = hist_metrics
        return result
