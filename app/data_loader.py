"""
Junction Data Loader for Frontend Dashboards.
Connects directly to SQLite database to load real junction records,
calibrated risk scores, and contributing factors adhering strictly to the
exact JunctionRecord schema contract.
"""

import os
import sys
import json
import sqlite3
from typing import List, Optional

# Ensure that the root directory is on the python path so we can import from src
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.schema import JunctionRecord
from src.database import init_db, get_db_connection

def load_junctions() -> List[JunctionRecord]:
    """
    Loads real junction records from the database with real calibrated risk scores,
    risk levels (LOW / MEDIUM / HIGH), and explainable contributing factors.
    Returns data in the EXACT existing List[JunctionRecord] schema contract.
    """
    # Ensure database tables and seed records are initialized
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM junctions ORDER BY risk_score DESC")
    rows = cursor.fetchall()
    conn.close()

    records: List[JunctionRecord] = []
    for r in rows:
        factors = json.loads(r["contributing_factors"]) if r["contributing_factors"] else []
        score = float(r["risk_score"]) if r["risk_score"] is not None else None
        level = r["risk_level"] or JunctionRecord.calculate_risk_level(score)
        
        record = JunctionRecord(
            junction_id=str(r["junction_id"]),
            name=str(r["name"]),
            lat=float(r["lat"]),
            lon=float(r["lon"]),
            city=str(r["city"]) if "city" in r.keys() and r["city"] else None,
            state=str(r["state"]) if "state" in r.keys() and r["state"] else None,
            risk_score=score,
            risk_level=level,
            contributing_factors=factors,
            last_updated=str(r["last_updated"]) if r["last_updated"] else None
        )
        records.append(record)

    return records

if __name__ == "__main__":
    j_list = load_junctions()
    print(f"[DataLoader] Loaded {len(j_list)} real junction records from DB:")
    for j in j_list:
        print(f"  - {j.junction_id}: {j.name} -> Score: {j.risk_score} ({j.risk_level})")
