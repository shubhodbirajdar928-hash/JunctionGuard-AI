"""
Database Manager for JunctionGuard AI (SQLite / Supabase).
Handles persistence and queries for:
  - junctions
  - detection_indicators
  - risk_scores (with contributing factors breakdown)
  - citizen_reports
  - accident_history & vision_logs
Includes migration utilities for citizen_reports JSON files and CRUD access functions.
"""

import sqlite3
import json
import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.schema import JunctionRecord

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "junctions.db")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "data", "citizen_reports")
REPORTS_JSON_PATH = os.path.join(REPORTS_DIR, "reports.json")
REPORTS_INDEX_JSON_PATH = os.path.join(REPORTS_DIR, "reports_index.json")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates database schema and populates initial sample Indian junction data."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Junctions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS junctions (
            junction_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            city TEXT,
            state TEXT,
            risk_score REAL,
            risk_level TEXT,
            contributing_factors TEXT,
            last_updated TEXT
        )
    """)

    # Add city/state columns if migrating existing older table
    try:
        cursor.execute("ALTER TABLE junctions ADD COLUMN city TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE junctions ADD COLUMN state TEXT")
    except Exception:
        pass

    # 2. Detection Indicators Table (Track A Vision Outputs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detection_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junction_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            traffic_density REAL,
            speed_proxy REAL,
            pedestrian_activity REAL,
            conflict_proxy INTEGER,
            two_wheeler_share_pct REAL,
            source_video TEXT,
            raw_metrics TEXT,
            FOREIGN KEY (junction_id) REFERENCES junctions (junction_id)
        )
    """)

    # 3. Risk Scores Table (with Contributing Factors Breakdown)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junction_id TEXT NOT NULL,
            risk_score REAL NOT NULL,
            risk_level TEXT NOT NULL,
            contributing_factors TEXT NOT NULL,
            historical_score REAL,
            traffic_score REAL,
            conflict_score REAL,
            pedestrian_score REAL,
            citizen_score REAL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (junction_id) REFERENCES junctions (junction_id)
        )
    """)

    # 4. Citizen Reports Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS citizen_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE,
            junction_id TEXT,
            reporter_name TEXT,
            issue_type TEXT,
            severity INTEGER,
            description TEXT,
            media_filename TEXT,
            media_relative_path TEXT,
            timestamp TEXT,
            FOREIGN KEY (junction_id) REFERENCES junctions (junction_id)
        )
    """)

    try:
        cursor.execute("ALTER TABLE citizen_reports ADD COLUMN report_id TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE citizen_reports ADD COLUMN media_filename TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE citizen_reports ADD COLUMN media_relative_path TEXT")
    except Exception:
        pass

    # 5. Accident History Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accident_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junction_id TEXT,
            year INTEGER,
            month TEXT,
            severity TEXT,
            fatalities INTEGER,
            injuries INTEGER,
            weather TEXT,
            road_type TEXT,
            vehicle_types TEXT,
            FOREIGN KEY (junction_id) REFERENCES junctions (junction_id)
        )
    """)

    # 6. Vision Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vision_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junction_id TEXT,
            timestamp TEXT,
            total_vehicles INTEGER,
            two_wheelers INTEGER,
            pedestrians INTEGER,
            congestion_score REAL,
            near_miss_count INTEGER,
            FOREIGN KEY (junction_id) REFERENCES junctions (junction_id)
        )
    """)

    conn.commit()

    # Seed Default Indian Junctions if empty or incomplete
    cursor.execute("SELECT COUNT(*) FROM junctions")
    count = cursor.fetchone()[0]
    if count < 12:
        seed_junctions(conn)

    conn.close()

    # Migrate any existing citizen reports JSON files into database
    migrate_citizen_reports_json()

def seed_junctions(conn):
    """Seed all 12 key Indian junctions (Metro Hubs + Kolhapur Hubs) with calibrated real data."""
    sample_junctions = [
        # 1. Bengaluru - Silk Board
        {
            "junction_id": "JNC-BLR-001",
            "name": "Silk Board Junction, Bengaluru",
            "lat": 12.9172,
            "lon": 77.6228,
            "city": "Bengaluru",
            "state": "Karnataka",
            "risk_score": 88.4,
            "risk_level": "HIGH",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.35},
                {"factor": "Extreme Congestion & Traffic Density", "weight": 0.28},
                {"factor": "Two-Wheeler Weaving & Near-Misses", "weight": 0.22},
                {"factor": "Citizen Hazard Reports", "weight": 0.15}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 2. New Delhi - ITO Crossing
        {
            "junction_id": "JNC-DEL-002",
            "name": "ITO Crossing, New Delhi",
            "lat": 28.6289,
            "lon": 77.2415,
            "city": "New Delhi",
            "state": "Delhi",
            "risk_score": 76.2,
            "risk_level": "HIGH",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.38},
                {"factor": "High Intersection Speed Differentials", "weight": 0.27},
                {"factor": "Pedestrian Jaywalking Hazards", "weight": 0.20},
                {"factor": "Poor Night Lighting", "weight": 0.15}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 3. Mumbai - Dadar TT Circle
        {
            "junction_id": "JNC-MUM-003",
            "name": "Dadar TT Circle, Mumbai",
            "lat": 19.0178,
            "lon": 72.8478,
            "city": "Mumbai",
            "state": "Maharashtra",
            "risk_score": 58.5,
            "risk_level": "MEDIUM",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.32},
                {"factor": "High Bus & Heavy Vehicle Mixing", "weight": 0.30},
                {"factor": "Citizen Hazard Reports", "weight": 0.22},
                {"factor": "Monsoon Visibility Reduction", "weight": 0.16}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 4. Chennai - Kathipara Junction
        {
            "junction_id": "JNC-MAA-004",
            "name": "Kathipara Junction, Chennai",
            "lat": 13.0067,
            "lon": 80.2020,
            "city": "Chennai",
            "state": "Tamil Nadu",
            "risk_score": 42.0,
            "risk_level": "MEDIUM",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.34},
                {"factor": "Flyover Merge Speed Mismatch", "weight": 0.31},
                {"factor": "Intermittent Signal Skipping", "weight": 0.20},
                {"factor": "Citizen Hazard Reports", "weight": 0.15}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 5. Hyderabad - Panjagutta Junction
        {
            "junction_id": "JNC-HYD-005",
            "name": "Panjagutta Junction, Hyderabad",
            "lat": 17.4256,
            "lon": 78.4514,
            "city": "Hyderabad",
            "state": "Telangana",
            "risk_score": 64.8,
            "risk_level": "MEDIUM",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.36},
                {"factor": "U-turn Collision Frequency", "weight": 0.26},
                {"factor": "High Two-Wheeler Density", "weight": 0.22},
                {"factor": "Signal Wait Time Frustration", "weight": 0.16}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 6. Bengaluru - Goraguntepalya Junction
        {
            "junction_id": "JNC-BLR-006",
            "name": "Goraguntepalya Junction, Bengaluru",
            "lat": 13.0285,
            "lon": 77.5404,
            "city": "Bengaluru",
            "state": "Karnataka",
            "risk_score": 82.1,
            "risk_level": "HIGH",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.40},
                {"factor": "Heavy Goods Truck Bottleneck", "weight": 0.28},
                {"factor": "Lack of Dedicated Pedestrian Subways", "weight": 0.18},
                {"factor": "Citizen Hazard Reports", "weight": 0.14}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 7. Pune - Chandani Chowk Junction
        {
            "junction_id": "JNC-PNQ-007",
            "name": "Chandani Chowk Junction, Pune",
            "lat": 18.5074,
            "lon": 73.7806,
            "city": "Pune",
            "state": "Maharashtra",
            "risk_score": 31.5,
            "risk_level": "LOW",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.38},
                {"factor": "Slope Incline Braking Distance", "weight": 0.32},
                {"factor": "Occasional Fog / Rain", "weight": 0.18},
                {"factor": "Citizen Hazard Reports", "weight": 0.12}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 8. Kolhapur - Shivaji Chowk
        {
            "junction_id": "J001",
            "name": "Shivaji Chowk",
            "lat": 16.6996,
            "lon": 74.2433,
            "city": "Kolhapur",
            "state": "Maharashtra",
            "risk_score": 38.0,
            "risk_level": "LOW",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.38},
                {"factor": "Pedestrian Market Density", "weight": 0.26},
                {"factor": "Two-Wheeler Congestion", "weight": 0.20},
                {"factor": "Citizen Hazard Reports", "weight": 0.16}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 9. Kolhapur - Rajaram Corner
        {
            "junction_id": "J002",
            "name": "Rajaram Corner",
            "lat": 16.7025,
            "lon": 74.2505,
            "city": "Kolhapur",
            "state": "Maharashtra",
            "risk_score": 36.0,
            "risk_level": "LOW",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.40},
                {"factor": "Secondary Arterial Crossroad Traffic", "weight": 0.25},
                {"factor": "Signal Timing Delay", "weight": 0.20},
                {"factor": "Citizen Hazard Reports", "weight": 0.15}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 10. Kolhapur - Dabholkar Corner
        {
            "junction_id": "J003",
            "name": "Dabholkar Corner",
            "lat": 16.7001,
            "lon": 74.2482,
            "city": "Kolhapur",
            "state": "Maharashtra",
            "risk_score": 40.8,
            "risk_level": "MEDIUM",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.36},
                {"factor": "Railway Station Transit Congestion", "weight": 0.28},
                {"factor": "Auto-Rickshaw Queuing Conflicts", "weight": 0.22},
                {"factor": "Citizen Hazard Reports", "weight": 0.14}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 11. Kolhapur - Cyber Chowk
        {
            "junction_id": "J004",
            "name": "Cyber Chowk",
            "lat": 16.6853,
            "lon": 74.2541,
            "city": "Kolhapur",
            "state": "Maharashtra",
            "risk_score": 34.0,
            "risk_level": "LOW",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.42},
                {"factor": "Student Pedestrian Activity", "weight": 0.26},
                {"factor": "Two-Wheeler Speeding", "weight": 0.18},
                {"factor": "Citizen Hazard Reports", "weight": 0.14}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        # 12. Kolhapur - Kawala Naka
        {
            "junction_id": "J005",
            "name": "Kawala Naka",
            "lat": 16.7018,
            "lon": 74.2575,
            "city": "Kolhapur",
            "state": "Maharashtra",
            "risk_score": 42.4,
            "risk_level": "MEDIUM",
            "contributing_factors": [
                {"factor": "Historical Accident Severity", "weight": 0.35},
                {"factor": "National Highway Entry Merging Speed", "weight": 0.30},
                {"factor": "Heavy Freight Inflow", "weight": 0.20},
                {"factor": "Citizen Hazard Reports", "weight": 0.15}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    ]

    cursor = conn.cursor()
    for jnc in sample_junctions:
        cursor.execute("""
            INSERT OR REPLACE INTO junctions 
            (junction_id, name, lat, lon, city, state, risk_score, risk_level, contributing_factors, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jnc["junction_id"],
            jnc["name"],
            jnc["lat"],
            jnc["lon"],
            jnc.get("city", "India"),
            jnc.get("state", "India"),
            jnc["risk_score"],
            jnc["risk_level"],
            json.dumps(jnc["contributing_factors"]),
            jnc["last_updated"]
        ))

        cursor.execute("""
            INSERT INTO risk_scores
            (junction_id, risk_score, risk_level, contributing_factors, historical_score, traffic_score, conflict_score, pedestrian_score, citizen_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jnc["junction_id"],
            jnc["risk_score"],
            jnc["risk_level"],
            json.dumps(jnc["contributing_factors"]),
            jnc["risk_score"] * 0.95,
            jnc["risk_score"] * 0.90,
            jnc["risk_score"] * 0.85,
            jnc["risk_score"] * 0.70,
            jnc["risk_score"] * 0.60,
            jnc["last_updated"]
        ))
    conn.commit()

# ============================================================
# SAVE / READ FUNCTIONS (REQUIRED BY SPECIFICATION)
# ============================================================

def save_risk_score(
    junction_id: str,
    risk_score: float,
    contributing_factors: List[Dict[str, Any]],
    component_scores: Optional[Dict[str, float]] = None
) -> bool:
    """
    Saves a calculated risk score and its contributing factors breakdown
    into the `risk_scores` history table and updates the `junctions` table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    risk_level = JunctionRecord.calculate_risk_level(risk_score)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    factors_json = json.dumps(contributing_factors)

    comps = component_scores or {}
    hist_s = comps.get("historical_accidents", comps.get("historical_score", 0.0))
    traf_s = comps.get("traffic_density", comps.get("traffic_score", 0.0))
    conf_s = comps.get("near_miss_conflicts", comps.get("conflict_score", 0.0))
    ped_s = comps.get("pedestrian_activity", comps.get("pedestrian_score", 0.0))
    cit_s = comps.get("citizen_hazard_reports", comps.get("citizen_score", 0.0))

    try:
        cursor.execute("""
            INSERT INTO risk_scores
            (junction_id, risk_score, risk_level, contributing_factors, historical_score, traffic_score, conflict_score, pedestrian_score, citizen_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (junction_id, risk_score, risk_level, factors_json, hist_s, traf_s, conf_s, ped_s, cit_s, now_str))

        cursor.execute("""
            UPDATE junctions
            SET risk_score = ?, risk_level = ?, contributing_factors = ?, last_updated = ?
            WHERE junction_id = ?
        """, (risk_score, risk_level, factors_json, now_str, junction_id))

        conn.commit()
        success = True
    except Exception as e:
        print(f"[Database Error] save_risk_score failed: {e}")
        success = False
    finally:
        conn.close()

    try:
        from src.supabase_client import update_junction_risk_supabase
        update_junction_risk_supabase(junction_id, risk_score, risk_level, contributing_factors)
    except Exception:
        pass

    return success

def get_junction_scores(junction_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Reads junction risk scores.
    If junction_id is provided, returns all recorded score history entries for that junction.
    If junction_id is None, returns the latest risk score for all junctions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if junction_id:
        cursor.execute("""
            SELECT * FROM risk_scores 
            WHERE junction_id = ? 
            ORDER BY id DESC
        """, (junction_id,))
        rows = cursor.fetchall()
    else:
        cursor.execute("""
            SELECT j.junction_id, j.name, j.lat, j.lon, j.city, j.state,
                   j.risk_score, j.risk_level, j.contributing_factors, j.last_updated
            FROM junctions j
            ORDER BY j.risk_score DESC
        """)
        rows = cursor.fetchall()

    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        if "contributing_factors" in item and item["contributing_factors"]:
            try:
                item["contributing_factors"] = json.loads(item["contributing_factors"])
            except Exception:
                pass
        results.append(item)
    return results

def save_detection_result(
    junction_id: str,
    traffic_density: float,
    speed_proxy: float,
    pedestrian_activity: float,
    conflict_proxy: int,
    two_wheeler_share_pct: float = 0.0,
    source_video: Optional[str] = None,
    raw_metrics: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Saves real-time Track A YOLO detection indicators into `detection_indicators` table
    and updates `vision_logs`.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_json = json.dumps(raw_metrics) if raw_metrics else None

    try:
        cursor.execute("""
            INSERT INTO detection_indicators
            (junction_id, timestamp, traffic_density, speed_proxy, pedestrian_activity, conflict_proxy, two_wheeler_share_pct, source_video, raw_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            junction_id, now_str, traffic_density, speed_proxy, pedestrian_activity,
            conflict_proxy, two_wheeler_share_pct, source_video, raw_json
        ))

        total_veh = int(round(traffic_density))
        two_w = int(round(total_veh * (two_wheeler_share_pct / 100.0)))
        peds = int(round(pedestrian_activity))
        congestion = min(100.0, (traffic_density / 30.0) * 100.0)

        cursor.execute("""
            INSERT INTO vision_logs
            (junction_id, timestamp, total_vehicles, two_wheelers, pedestrians, congestion_score, near_miss_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (junction_id, now_str, total_veh, two_w, peds, congestion, conflict_proxy))

        conn.commit()
        success = True
    except Exception as e:
        print(f"[Database Error] save_detection_result failed: {e}")
        success = False
    finally:
        conn.close()

    try:
        from src.supabase_client import insert_detection_indicator
        insert_detection_indicator({
            "junction_id": junction_id,
            "source_video": source_video or "live_stream.mp4",
            "traffic_density": traffic_density,
            "speed_proxy": speed_proxy,
            "pedestrian_activity": pedestrian_activity,
            "conflict_proxy": conflict_proxy,
            "two_wheeler_share_pct": two_wheeler_share_pct
        })
    except Exception:
        pass

    return success

# ============================================================
# CITIZEN REPORTS MIGRATION & QUERYING
# ============================================================

def migrate_citizen_reports_json(json_path: Optional[str] = None) -> int:
    """
    Migrates existing citizen reports from JSON files (reports.json or reports_index.json)
    into the SQLite `citizen_reports` table.
    Returns the count of new migrated records.
    """
    candidate_paths = [json_path] if json_path else [REPORTS_JSON_PATH, REPORTS_INDEX_JSON_PATH]
    found_reports = []

    for path in candidate_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        found_reports.extend(data)
            except Exception as e:
                print(f"[Migration Note] Error reading {path}: {e}")

    if not found_reports:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()
    migrated_count = 0

    for rep in found_reports:
        rep_id = rep.get("report_id") or rep.get("id") or str(uuid.uuid4().hex[:12])
        jnc_id = rep.get("junction_id", "J001")
        name = rep.get("reporter_name", "Anonymous")
        desc = rep.get("description", "")
        issue = rep.get("issue_type") or (desc.split(":")[0] if ":" in desc else "Citizen Hazard")
        sev = int(rep.get("severity", 4))
        media_fn = rep.get("media_filename")
        media_rp = rep.get("media_relative_path")
        ts = rep.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO citizen_reports
                (report_id, junction_id, reporter_name, issue_type, severity, description, media_filename, media_relative_path, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rep_id, jnc_id, name, issue, sev, desc, media_fn, media_rp, ts))
            migrated_count += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return migrated_count

def add_citizen_report(
    junction_id: str,
    reporter: str,
    issue: str,
    severity: int,
    description: str,
    media_filename: Optional[str] = None,
    media_relative_path: Optional[str] = None
) -> bool:
    """Inserts a new citizen report into both SQLite DB and Supabase."""
    conn = get_db_connection()
    cursor = conn.cursor()
    report_id = f"REP-{uuid.uuid4().hex[:10].upper()}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO citizen_reports 
        (report_id, junction_id, reporter_name, issue_type, severity, description, media_filename, media_relative_path, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (report_id, junction_id, reporter, issue, severity, description, media_filename, media_relative_path, now_str))
    conn.commit()
    conn.close()

    try:
        from src.supabase_client import insert_citizen_report_supabase
        insert_citizen_report_supabase({
            "report_id": report_id,
            "junction_id": junction_id,
            "reporter_name": reporter,
            "description": f"{issue}: {description} (Severity: {severity}/5)",
            "status": "PENDING_REVIEW"
        })
    except Exception:
        pass

    return True

def fetch_citizen_reports(junction_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches citizen reports from local SQLite DB with fallback to Supabase."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if junction_id:
        cursor.execute("SELECT * FROM citizen_reports WHERE junction_id = ? ORDER BY id DESC", (junction_id,))
    else:
        cursor.execute("SELECT * FROM citizen_reports ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    local_reports = [dict(r) for r in rows]
    if local_reports:
        return local_reports

    try:
        from src.supabase_client import fetch_citizen_reports_supabase
        sb_reports = fetch_citizen_reports_supabase(junction_id)
        if sb_reports:
            formatted = []
            for r in sb_reports:
                desc = r.get("description", "")
                issue_type = desc.split(":")[0] if ":" in desc else "Citizen Hazard Report"
                formatted.append({
                    "id": r.get("report_id"),
                    "report_id": r.get("report_id"),
                    "junction_id": r.get("junction_id"),
                    "reporter_name": r.get("reporter_name", "Anonymous"),
                    "issue_type": issue_type,
                    "severity": 4,
                    "description": desc,
                    "timestamp": r.get("submitted_at", "")[:19].replace("T", " ")
                })
            return formatted
    except Exception:
        pass

    return []

# ============================================================
# JUNCTIONS QUERY FUNCTIONS
# ============================================================

def fetch_all_junctions() -> List[Dict[str, Any]]:
    """Fetch all junctions adhering strictly to data contract."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM junctions ORDER BY risk_score DESC")
    rows = cursor.fetchall()
    conn.close()

    junctions = []
    for r in rows:
        factors = json.loads(r["contributing_factors"]) if r["contributing_factors"] else []
        record = JunctionRecord(
            junction_id=r["junction_id"],
            name=r["name"],
            lat=float(r["lat"]),
            lon=float(r["lon"]),
            city=r["city"] if "city" in r.keys() else None,
            state=r["state"] if "state" in r.keys() else None,
            risk_score=r["risk_score"],
            risk_level=r["risk_level"],
            contributing_factors=factors,
            last_updated=r["last_updated"]
        )
        junctions.append(record.to_dict())
    return junctions

def fetch_junction_by_id(junction_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single junction record by ID."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM junctions WHERE junction_id = ?", (junction_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    factors = json.loads(row["contributing_factors"]) if row["contributing_factors"] else []
    record = JunctionRecord(
        junction_id=row["junction_id"],
        name=row["name"],
        lat=float(row["lat"]),
        lon=float(row["lon"]),
        city=row["city"] if "city" in row.keys() else None,
        state=row["state"] if "state" in row.keys() else None,
        risk_score=row["risk_score"],
        risk_level=row["risk_level"],
        contributing_factors=factors,
        last_updated=row["last_updated"]
    )
    return record.to_dict()

def update_junction_risk(junction_id: str, risk_score: float, factors: List[Dict[str, Any]]):
    """Update risk score and contributing factors for a junction (delegates to save_risk_score)."""
    return save_risk_score(junction_id, risk_score, factors)

if __name__ == "__main__":
    init_db()
    print("[Database] SQLite tables initialized and seed junctions loaded.")
