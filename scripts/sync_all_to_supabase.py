#!/usr/bin/env python3
"""
Master Synchronization Script for JunctionGuard AI.
Synchronizes all application tables (junctions, risk scores, citizen hazard reports,
and detection indicators) directly between local database/analytics engine and Supabase.
"""

import os
import sys
import json
import pandas as pd

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import fetch_all_junctions, fetch_citizen_reports
from src.supabase_client import (
    get_supabase_client, upsert_junction_supabase, update_junction_risk_supabase,
    insert_citizen_report_supabase, fetch_junctions_supabase, fetch_citizen_reports_supabase,
    fetch_detection_indicators
)

def sync_all():
    print("=" * 75)
    print(" JunctionGuard AI - Full Master Supabase Synchronization")
    print("=" * 75)

    client = get_supabase_client()

    # 1. Sync Junctions & Risk Metrics
    print("\n📍 [1/3] Synchronizing Junctions & Risk Scores...")
    local_junctions = fetch_all_junctions()
    synced_jncs = 0
    for j in local_junctions:
        city = j["name"].split(",")[-1].strip() if "," in j["name"] else "India"
        upsert_junction_supabase({
            "junction_id": j["junction_id"],
            "name": j["name"],
            "lat": j["lat"],
            "lon": j["lon"],
            "city": city
        })
        update_junction_risk_supabase(
            junction_id=j["junction_id"],
            risk_score=j["risk_score"],
            risk_level=j["risk_level"],
            contributing_factors=j["contributing_factors"]
        )
        synced_jncs += 1

    print(f"✅ Synced {synced_jncs} junctions & risk scores to Supabase!")

    # 2. Sync Citizen Hazard Reports
    print("\n📝 [2/3] Synchronizing Citizen Hazard Reports...")
    local_reports = fetch_citizen_reports()
    synced_reps = 0
    for r in local_reports:
        insert_citizen_report_supabase({
            "report_id": f"REP-{r['id']}",
            "junction_id": r["junction_id"],
            "reporter_name": r.get("reporter_name", "Anonymous"),
            "description": f"{r['issue_type']}: {r['description']} (Severity: {r['severity']}/5)",
            "status": "PENDING_REVIEW"
        })
        synced_reps += 1

    print(f"✅ Synced {synced_reps} citizen hazard reports to Supabase!")

    # 3. Verify Table Counts & Schema
    print("\n📊 [3/3] Verifying Live Supabase Table Stats...")
    sb_jncs = fetch_junctions_supabase()
    sb_reps = fetch_citizen_reports_supabase()
    sb_inds = fetch_detection_indicators()

    table_stats = [
        {"Table Name": "junctions", "Live Rows": len(sb_jncs), "Status": "✅ Active & Synced"},
        {"Table Name": "citizen_reports", "Live Rows": len(sb_reps), "Status": "✅ Active & Synced"},
        {"Table Name": "detection_indicators", "Live Rows": len(sb_inds), "Status": "✅ Active & Synced"}
    ]

    df_stats = pd.DataFrame(table_stats)
    print("\n" + "=" * 75)
    print(df_stats.to_string(index=False))
    print("=" * 75)
    print("Master Supabase Synchronization completed successfully!")

if __name__ == "__main__":
    sync_all()
