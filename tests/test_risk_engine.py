"""
Unit and integration tests for the Explainable Junction Risk Score Engine.
Tests standalone calculate_junction_risk_score() function, exact contributing_factors format,
weights summing to 1.0, and bounds [0.0, 100.0].
"""

import os
import sys
import unittest

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.risk_engine import (
    calculate_junction_risk_score,
    ExplainableRiskEngine,
    load_citizen_reports_data
)
from src.database import init_db

class TestJunctionRiskScoreEngine(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_standalone_scoring_function_with_indicators_dict(self):
        """Verify standalone calculate_junction_risk_score combines Track A, Track B, and citizen reports."""
        traffic_indicators = {
            "traffic_density": 18.5,       # 18.5 vehicles/frame
            "speed_proxy": 32.0,           # 32 px/s
            "conflict_proxy": 4,           # 4 near-miss events
            "pedestrian_activity": 3.0,    # 3 peds/frame
            "two_wheeler_share_pct": 55.0  # 55% motorcycles
        }
        accident_history_score = 88.0
        citizen_reports = [
            {"report_id": "R1", "severity": 4, "issue_type": "Pothole"},
            {"report_id": "R2", "severity": 5, "issue_type": "Near-Miss"}
        ]

        result = calculate_junction_risk_score(
            traffic_indicators=traffic_indicators,
            accident_history_score=accident_history_score,
            citizen_reports=citizen_reports,
            weather_condition="Clear"
        )

        # 1. Verify Return Structure
        self.assertIn("risk_score", result)
        self.assertIn("risk_level", result)
        self.assertIn("contributing_factors", result)
        self.assertIn("component_scores", result)

        # 2. Verify Score Bounds (0.0 to 100.0)
        score = result["risk_score"]
        self.assertTrue(0.0 <= score <= 100.0, f"Score {score} out of [0, 100] bounds")
        self.assertIn(result["risk_level"], ["LOW", "MEDIUM", "HIGH"])

        # 3. Verify Exact contributing_factors Format: [{"factor": "...", "weight": float}, ...]
        factors = result["contributing_factors"]
        self.assertIsInstance(factors, list)
        self.assertGreater(len(factors), 0)

        for factor_dict in factors:
            self.assertIn("factor", factor_dict)
            self.assertIn("weight", factor_dict)
            self.assertIsInstance(factor_dict["factor"], str)
            self.assertIsInstance(factor_dict["weight"], (float, int))
            self.assertTrue(0.0 <= factor_dict["weight"] <= 1.0)

        # 4. Verify Weights sum to roughly 1.0
        total_weight = sum(f["weight"] for f in factors)
        self.assertAlmostEqual(total_weight, 1.0, delta=0.02, msg=f"Factor weights sum to {total_weight}, expected ~1.0")

    def test_factor_format_example(self):
        """Verify the exact format requested: [{'factor': 'Pedestrian Activity', 'weight': 0.32}, ...]."""
        traffic_indicators = {"traffic_density": 5.0, "pedestrian_activity": 6.0, "conflict_proxy": 1}
        result = calculate_junction_risk_score(
            traffic_indicators=traffic_indicators,
            accident_history_score=40.0,
            citizen_reports=1
        )
        
        factors = result["contributing_factors"]
        factor_names = [f["factor"] for f in factors]
        self.assertIn("Pedestrian Activity", factor_names)
        self.assertIn("Historical Accident Severity", factor_names)
        
        # Verify all elements have exact keys and valid rounded values
        for f in factors:
            self.assertEqual(len(f), 2)
            self.assertTrue("factor" in f and "weight" in f)

    def test_monotonicity_and_explainability(self):
        """Verify that increasing conflicts or accident history strictly increases the composite risk score."""
        low_traffic = {"traffic_density": 4.0, "conflict_proxy": 0, "pedestrian_activity": 0.5}
        high_traffic = {"traffic_density": 25.0, "conflict_proxy": 10, "pedestrian_activity": 8.0}

        low_risk = calculate_junction_risk_score(
            traffic_indicators=low_traffic,
            accident_history_score=25.0,
            citizen_reports=0
        )["risk_score"]

        high_risk = calculate_junction_risk_score(
            traffic_indicators=high_traffic,
            accident_history_score=95.0,
            citizen_reports=5
        )["risk_score"]

        self.assertGreater(high_risk, low_risk, "High traffic & accident conditions must produce higher risk score")

    def test_explainable_risk_engine_integration(self):
        """Verify ExplainableRiskEngine class computes risk for real seeded junction."""
        engine = ExplainableRiskEngine()
        res = engine.compute_junction_risk("JNC-BLR-001", vision_indicators={"traffic_density": 20.0, "conflict_proxy": 5})

        self.assertEqual(res["junction_id"], "JNC-BLR-001")
        self.assertTrue(0.0 <= res["risk_score"] <= 100.0)
        self.assertIn("hist_metrics", res)

    def test_load_citizen_reports(self):
        """Verify load_citizen_reports_data returns list."""
        reports = load_citizen_reports_data()
        self.assertIsInstance(reports, list)

if __name__ == "__main__":
    unittest.main()
