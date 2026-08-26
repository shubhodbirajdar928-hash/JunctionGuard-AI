"""
Unit and Integration Tests for Full Supabase Synchronization Across All Application Tables.
"""

import os
import pytest
from src.supabase_client import (
    get_supabase_client, fetch_junctions_supabase, upsert_junction_supabase,
    fetch_citizen_reports_supabase, insert_citizen_report_supabase,
    fetch_detection_indicators
)
from src.database import fetch_all_junctions, fetch_citizen_reports, add_citizen_report

def test_supabase_junctions_crud():
    client = get_supabase_client()
    assert client is not None

    # Upsert test junction
    res = upsert_junction_supabase({
        "junction_id": "J001",
        "name": "Shivaji Chowk",
        "lat": 16.6996,
        "lon": 74.2433,
        "city": "Kolhapur"
    })
    assert res.get("junction_id") == "J001"

    # Fetch junctions list
    junctions = fetch_junctions_supabase()
    assert len(junctions) > 0
    assert any(j.get("junction_id") == "J001" for j in junctions)

def test_supabase_citizen_reports_crud():
    # Insert test citizen report
    report = insert_citizen_report_supabase({
        "report_id": "TEST-REP-999",
        "junction_id": "J001",
        "reporter_name": "Pytest Inspector",
        "description": "Test hazard report for sync verification",
        "status": "PENDING_REVIEW"
    })
    assert report.get("report_id") == "TEST-REP-999"

    # Fetch reports
    reports = fetch_citizen_reports_supabase("J001")
    assert len(reports) > 0
    assert any(r.get("report_id") == "TEST-REP-999" for r in reports)

    # Cleanup test report
    client = get_supabase_client()
    client.table("citizen_reports").delete().eq("report_id", "TEST-REP-999").execute()

def test_database_layer_supabase_integration():
    # Fetch citizen reports using database access layer
    reports = fetch_citizen_reports()
    assert isinstance(reports, list)
    assert len(reports) > 0
