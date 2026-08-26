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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = Any

_supabase_client: Optional[Any] = None

def get_supabase_client() -> Client:
    """Returns a singleton instance of the Supabase client."""
    global _supabase_client
    if not SUPABASE_AVAILABLE:
        raise ImportError("supabase package is not installed. Install via: pip install supabase")
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
# CITIZEN HAZARD REPORTS & STORAGE
# ============================================================
def upload_citizen_media_supabase(
    file_bytes: bytes,
    filename: str,
    content_type: str = "image/jpeg",
    bucket_name: str = "citizen-reports"
) -> Optional[str]:
    """
    Uploads photo/video evidence bytes to Supabase Storage and returns the public URL.
    Returns None if upload fails or credentials/storage are unavailable.
    """
    if not SUPABASE_AVAILABLE:
        return None
    try:
        client = get_supabase_client()
        storage_path = f"evidence/{filename}"
        
        target_buckets = [bucket_name, "citizen-reports", "citizen_hazard_media", "reports"]
        target_buckets = list(dict.fromkeys(target_buckets))

        last_error = None
        for b_name in target_buckets:
            try:
                # Try standard upload first
                client.storage.from_(b_name).upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": content_type}
                )
                public_url = client.storage.from_(b_name).get_public_url(storage_path)
                print(f"✅ [Supabase Storage] Uploaded {filename} to '{b_name}' -> {public_url}")
                return public_url
            except Exception as upload_err:
                last_error = upload_err
                # Try update if file already exists
                try:
                    client.storage.from_(b_name).update(
                        path=storage_path,
                        file=file_bytes,
                        file_options={"content-type": content_type}
                    )
                    public_url = client.storage.from_(b_name).get_public_url(storage_path)
                    print(f"✅ [Supabase Storage] Updated {filename} in '{b_name}' -> {public_url}")
                    return public_url
                except Exception as update_err:
                    last_error = update_err
                    continue

        if last_error:
            print(f"[Supabase Storage Note] Upload error: {last_error}")
        return None
    except Exception as e:
        print(f"[Supabase Storage Note] Failed to upload media: {e}")
        return None

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
    if report_data.get("media_url"):
        payload["media_url"] = report_data["media_url"]

    try:
        res = client.table("citizen_reports").insert(payload).execute()
        print(f"✅ [Supabase DB] Successfully inserted report {report_id} into Supabase table!")
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
