"""
SQLite Database Manager for JunctionGuard AI.
Handles persistence for junctions, accident history, citizen reports, and vision analytics.
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.schema import JunctionRecord

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "junctions.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates database schema and populates initial sample Indian junction data."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Junctions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS junctions (
            junction_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            risk_score REAL,
            risk_level TEXT,
            contributing_factors TEXT, -- JSON string
            last_updated TEXT
        )
    """)

    # Create Accident History Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accident_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junction_id TEXT,
            year INTEGER,
            month TEXT,
            severity TEXT, -- Fatal, Serious, Minor
            fatalities INTEGER,
            injuries INTEGER,
            weather TEXT,
            road_type TEXT,
            vehicle_types TEXT,
            FOREIGN KEY (junction_id) REFERENCES junctions (junction_id)
        )
    """)

    # Create Citizen Reports Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS citizen_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junction_id TEXT,
            reporter_name TEXT,
            issue_type TEXT, -- Pothole, Broken Traffic Light, Blind Spot, Speeding, Near-Miss
            severity INTEGER, -- 1-5
            description TEXT,
            timestamp TEXT,
            FOREIGN KEY (junction_id) REFERENCES junctions (junction_id)
        )
    """)

    # Create Vision Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vision_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junction_id TEXT,
            timestamp TEXT,
            total_vehicles INTEGER,
            two_wheelers INTEGER,
            pedestrians INTEGER,
            congestion_score REAL, -- 0-100
            near_miss_count INTEGER,
            FOREIGN KEY (junction_id) REFERENCES junctions (junction_id)
        )
    """)

    conn.commit()

    # Seed Default Indian Junctions if empty
    cursor.execute("SELECT COUNT(*) FROM junctions")
    if cursor.fetchone()[0] == 0:
        seed_junctions(conn)

    conn.close()

def seed_junctions(conn):
    """Seed key high-traffic Indian junctions with realistic data."""
    sample_junctions = [
        {
            "junction_id": "JNC-BLR-001",
            "name": "Silk Board Junction, Bengaluru",
            "lat": 12.9172,
            "lon": 77.6228,
            "risk_score": 88.4,
            "risk_level": "HIGH",
            "contributing_factors": [
                {"factor": "Extreme Congestion & Traffic Volume", "weight": 0.38},
                {"factor": "High Historical Accident Severity", "weight": 0.32},
                {"factor": "Two-Wheeler Weaving & Near-Misses", "weight": 0.18},
                {"factor": "Potholes & Construction Hazards", "weight": 0.12}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "junction_id": "JNC-DEL-002",
            "name": "ITO Crossing, New Delhi",
            "lat": 28.6289,
            "lon": 77.2415,
            "risk_score": 76.2,
            "risk_level": "HIGH",
            "contributing_factors": [
                {"factor": "High Intersection Speed Differentials", "weight": 0.40},
                {"factor": "Pedestrian Jaywalking Hazards", "weight": 0.30},
                {"factor": "Historical Fatalities (2018-2023)", "weight": 0.20},
                {"factor": "Poor Night Lighting", "weight": 0.10}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "junction_id": "JNC-MUM-003",
            "name": "Dadar TT Circle, Mumbai",
            "lat": 19.0178,
            "lon": 72.8478,
            "risk_score": 58.5,
            "risk_level": "MEDIUM",
            "contributing_factors": [
                {"factor": "High Bus & Heavy Vehicle Mixing", "weight": 0.45},
                {"factor": "Monsoon Visibility Reduction", "weight": 0.25},
                {"factor": "Citizen Hazard Reports", "weight": 0.20},
                {"factor": "Low Pedestrian Crossing Safety", "weight": 0.10}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "junction_id": "JNC-MAA-004",
            "name": "Kathipara Junction, Chennai",
            "lat": 13.0067,
            "lon": 80.2020,
            "risk_score": 42.0,
            "risk_level": "MEDIUM",
            "contributing_factors": [
                {"factor": "Flyover Merge Speed Mismatch", "weight": 0.50},
                {"factor": "Intermittent Signal Skipping", "weight": 0.30},
                {"factor": "Night-time Speeding", "weight": 0.20}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "junction_id": "JNC-HYD-005",
            "name": "Panjagutta Junction, Hyderabad",
            "lat": 17.4256,
            "lon": 78.4514,
            "risk_score": 64.8,
            "risk_level": "MEDIUM",
            "contributing_factors": [
                {"factor": "U-turn Collision Frequency", "weight": 0.40},
                {"factor": "High Two-Wheeler Density", "weight": 0.35},
                {"factor": "Signal Wait Time Frustration", "weight": 0.25}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "junction_id": "JNC-BLR-006",
            "name": "Goraguntepalya Junction, Bengaluru",
            "lat": 13.0285,
            "lon": 77.5404,
            "risk_score": 82.1,
            "risk_level": "HIGH",
            "contributing_factors": [
                {"factor": "Heavy Goods Truck Traffic Bottleneck", "weight": 0.42},
                {"factor": "High Historical Serious Injuries", "weight": 0.33},
                {"factor": "Lack of Dedicated Pedestrian Subways", "weight": 0.25}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "junction_id": "JNC-PNQ-007",
            "name": "Chandani Chowk Junction, Pune",
            "lat": 18.5074,
            "lon": 73.7806,
            "risk_score": 31.5,
            "risk_level": "LOW",
            "contributing_factors": [
                {"factor": "Slope Incline Braking Distance", "weight": 0.55},
                {"factor": "Occasional Fog / Rain", "weight": 0.45}
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    ]

    cursor = conn.cursor()
    for jnc in sample_junctions:
        cursor.execute("""
            INSERT OR REPLACE INTO junctions 
            (junction_id, name, lat, lon, risk_score, risk_level, contributing_factors, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jnc["junction_id"],
            jnc["name"],
            jnc["lat"],
            jnc["lon"],
            jnc["risk_score"],
            jnc["risk_level"],
            json.dumps(jnc["contributing_factors"]),
            jnc["last_updated"]
        ))
    conn.commit()

def fetch_all_junctions() -> List[Dict[str, Any]]:
    """Fetch all junctions adhering strictly to data contract."""
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
            lat=r["lat"],
            lon=r["lon"],
            risk_score=r["risk_score"],
            risk_level=r["risk_level"],
            contributing_factors=factors,
            last_updated=r["last_updated"]
        )
        junctions.append(record.to_dict())
    return junctions

def fetch_junction_by_id(junction_id: str) -> Optional[Dict[str, Any]]:
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
        lat=row["lat"],
        lon=row["lon"],
        risk_score=row["risk_score"],
        risk_level=row["risk_level"],
        contributing_factors=factors,
        last_updated=row["last_updated"]
    )
    return record.to_dict()

def update_junction_risk(junction_id: str, risk_score: float, factors: List[Dict[str, float]]):
    """Update risk score and contributing factors for a junction."""
    conn = get_db_connection()
    cursor = conn.cursor()
    risk_level = JunctionRecord.calculate_risk_level(risk_score)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE junctions
        SET risk_score = ?, risk_level = ?, contributing_factors = ?, last_updated = ?
        WHERE junction_id = ?
    """, (risk_score, risk_level, json.dumps(factors), now_str, junction_id))
    conn.commit()
    conn.close()

def add_citizen_report(junction_id: str, reporter: str, issue: str, severity: int, description: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO citizen_reports (junction_id, reporter_name, issue_type, severity, description, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (junction_id, reporter, issue, severity, description, now_str))
    conn.commit()
    conn.close()

def fetch_citizen_reports(junction_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if junction_id:
        cursor.execute("SELECT * FROM citizen_reports WHERE junction_id = ? ORDER BY id DESC", (junction_id,))
    else:
        cursor.execute("SELECT * FROM citizen_reports ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
