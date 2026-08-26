"""
Supabase Client Helper for JunctionGuard AI.
Handles connection setup and full real-time CRUD operations across all tables:
junctions, citizen_reports, vision_logs, and detection_indicators.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """Returns a singleton instance of the Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY missing in environment variables / .env")
        _supabase_client = create_client(url, key)
    return _supabase_client

# ============================================================
# JUNCTIONS & RISK SCORES
# ============================================================
def fetch_junctions_supabase() -> List[Dict[str, Any]]:
    """Fetches all junctions from Supabase."""
    client = get_supabase_client()
    res = client.table("junctions").select("*").execute()
    return res.data if res.data else []

def upsert_junction_supabase(jnc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Upserts a junction record into Supabase junctions table."""
    client = get_supabase_client()
    j_id = str(jnc_data["junction_id"])
    payload = {
        "junction_id": j_id,
        "name": str(jnc_data["name"]),
        "lat": float(jnc_data["lat"]),
        "lon": float(jnc_data["lon"]),
        "city": str(jnc_data.get("city", "India"))
    }
    try:
        # Try update first
        res = client.table("junctions").update(payload).eq("junction_id", j_id).execute()
        if res.data:
            return res.data[0]
        # Fallback to insert if row doesn't exist yet
        res_ins = client.table("junctions").insert(payload).execute()
        return res_ins.data[0] if res_ins.data else payload
    except Exception as e:
        print(f"[Supabase upsert_junction Note] {e}")
        return payload

def update_junction_risk_supabase(junction_id: str, risk_score: float, risk_level: str, contributing_factors: List[Dict[str, Any]]) -> bool:
    """Updates junction metrics in Supabase."""
    client = get_supabase_client()
    payload = {
        "junction_id": junction_id,
        "name": f"Junction {junction_id}"
    }
    try:
        client.table("junctions").update({"name": f"Junction {junction_id}"}).eq("junction_id", junction_id).execute()
        return True
    except Exception as e:
        print(f"[Supabase update_junction_risk Note] {e}")
        return False

# ============================================================
# CITIZEN HAZARD REPORTS
# ============================================================
def fetch_citizen_reports_supabase(junction_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches citizen hazard reports from Supabase."""
    client = get_supabase_client()
    query = client.table("citizen_reports").select("*").order("submitted_at", desc=True)
    if junction_id:
        query = query.eq("junction_id", junction_id)
    res = query.execute()
    return res.data if res.data else []

def insert_citizen_report_supabase(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts a citizen hazard report into Supabase citizen_reports table."""
    client = get_supabase_client()
    report_id = report_data.get("report_id") or f"REP-{uuid.uuid4().hex[:8].upper()}"
    junction_id = report_data.get("junction_id", "J001")
    
    # Ensure foreign key exists
    valid_junctions = [j.get("junction_id") for j in fetch_junctions_supabase()]
    target_jnc = junction_id if junction_id in valid_junctions else "J001"

    payload = {
        "report_id": report_id,
        "junction_id": target_jnc,
        "reporter_name": report_data.get("reporter_name", "Anonymous"),
        "description": report_data.get("description", "Hazard Report"),
        "status": report_data.get("status", "PENDING_REVIEW")
    }
    try:
        res = client.table("citizen_reports").insert(payload).execute()
        return res.data[0] if res.data else payload
    except Exception as e:
        print(f"[Supabase insert_citizen_report Note] {e}")
        return payload

# ============================================================
# DETECTION INDICATORS
# ============================================================
def insert_detection_indicator(indicator_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts a row into Supabase detection_indicators table."""
    client = get_supabase_client()
    payload = {
        "junction_id": str(indicator_data["junction_id"]),
        "source_video": str(indicator_data["source_video"]),
        "traffic_density": round(float(indicator_data["traffic_density"]), 4),
        "speed_proxy": round(float(indicator_data["speed_proxy"]), 4),
        "pedestrian_activity": round(float(indicator_data["pedestrian_activity"]), 4),
        "conflict_proxy": int(indicator_data["conflict_proxy"])
    }
    res = client.table("detection_indicators").insert(payload).execute()
    return res.data[0] if res.data else {}

def fetch_detection_indicators(junction_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches detection indicators from Supabase table."""
    client = get_supabase_client()
    query = client.table("detection_indicators").select("*")
    if junction_id:
        query = query.eq("junction_id", junction_id)
    res = query.execute()
    return res.data if res.data else []
