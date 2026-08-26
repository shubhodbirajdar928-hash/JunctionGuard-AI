"""
Unit and integration tests for SQLite Database Layer and CRUD operations.
Tests save_risk_score, get_junction_scores, save_detection_result, citizen reports migration,
and data_loader.load_junctions schema adherence.
"""

import os
import sys
import json
import unittest
import tempfile

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import (
    init_db,
    save_risk_score,
    get_junction_scores,
    save_detection_result,
    migrate_citizen_reports_json,
    fetch_all_junctions,
    fetch_junction_by_id,
    fetch_citizen_reports
)
from app.data_loader import load_junctions
from src.schema import JunctionRecord

class TestDatabaseCRUD(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_save_and_get_risk_scores(self):
        """Test save_risk_score inserts into risk_scores table and updates junction record."""
        factors = [
            {"factor": "Pedestrian Density", "weight": 0.50},
            {"factor": "Speed Differential", "weight": 0.50}
        ]
        component_scores = {
            "historical_accidents": 75.0,
            "traffic_density": 80.0,
            "near_miss_conflicts": 85.0,
            "pedestrian_activity": 60.0,
            "citizen_hazard_reports": 50.0
        }

        success = save_risk_score(
            junction_id="JNC-BLR-001",
            risk_score=85.5,
            contributing_factors=factors,
            component_scores=component_scores
        )
        self.assertTrue(success)

        # Test get_junction_scores for specific junction
        history = get_junction_scores("JNC-BLR-001")
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)
        latest_entry = history[0]
        self.assertEqual(latest_entry["junction_id"], "JNC-BLR-001")
        self.assertEqual(float(latest_entry["risk_score"]), 85.5)
        self.assertEqual(latest_entry["risk_level"], "HIGH")

        # Test get_junction_scores for all junctions
        all_scores = get_junction_scores()
        self.assertIsInstance(all_scores, list)
        self.assertGreaterEqual(len(all_scores), 12)

    def test_save_detection_result(self):
        """Test saving Track A vision detection indicators into detection_indicators table."""
        success = save_detection_result(
            junction_id="J001",
            traffic_density=16.5,
            speed_proxy=35.2,
            pedestrian_activity=4.0,
            conflict_proxy=3,
            two_wheeler_share_pct=60.0,
            source_video="indian_traffic_1.mp4",
            raw_metrics={"car": 8, "motorcycle": 12, "bus": 1}
        )
        self.assertTrue(success)

    def test_migrate_citizen_reports_json(self):
        """Test migrating citizen reports from JSON file into SQLite table."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            sample_reports = [
                {
                    "report_id": "TEST-REP-MIGRATE-1",
                    "junction_id": "J001",
                    "reporter_name": "Ravi Patil",
                    "description": "Pothole near signal: deep trench causing bike skidding",
                    "severity": 4,
                    "timestamp": "2026-08-26 10:00:00"
                }
            ]
            json.dump(sample_reports, f)
            temp_path = f.name

        try:
            count = migrate_citizen_reports_json(temp_path)
            self.assertGreaterEqual(count, 0)
            
            # Query reports
            reports = fetch_citizen_reports("J001")
            self.assertTrue(any(r.get("report_id") == "TEST-REP-MIGRATE-1" or "Pothole near signal" in str(r.get("description")) for r in reports))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_load_junctions_real_query_schema(self):
        """Verify app/data_loader.py load_junctions() returns real records with no None risk scores."""
        junctions = load_junctions()
        self.assertIsInstance(junctions, list)
        self.assertGreaterEqual(len(junctions), 12)

        for jnc in junctions:
            self.assertIsInstance(jnc, JunctionRecord)
            self.assertIsNotNone(jnc.risk_score, f"risk_score is None for {jnc.name}")
            self.assertTrue(0.0 <= jnc.risk_score <= 100.0)
            self.assertIn(jnc.risk_level, ["LOW", "MEDIUM", "HIGH"])
            self.assertIsNotNone(jnc.contributing_factors)
            self.assertGreater(len(jnc.contributing_factors), 0)

            for factor in jnc.contributing_factors:
                self.assertIn("factor", factor)
                self.assertIn("weight", factor)
                self.assertTrue(0.0 <= factor["weight"] <= 1.0)

if __name__ == "__main__":
    unittest.main()
