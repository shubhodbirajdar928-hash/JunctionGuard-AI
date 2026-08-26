"""
Unit tests verifying strict compliance with the JunctionGuard AI Data Contract Schema
and mathematical bounds of the Explainable Risk Engine.
Uses standard library unittest for zero external dependencies.
"""

import os
import sys
import unittest

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.schema import JunctionRecord, ContributingFactor
from src.database import init_db, fetch_all_junctions
from src.analytics.risk_engine import ExplainableRiskEngine
from src.analytics.data_loader import compute_historical_risk_score

class TestJunctionGuardDataContract(unittest.TestCase):
    
    def setUp(self):
        init_db()

    def test_data_contract_schema(self):
        """Verify that junction records match all required schema keys and types."""
        junctions = fetch_all_junctions()
        self.assertGreater(len(junctions), 0, "Database should contain seeded sample junctions.")

        required_keys = {
            "junction_id", "name", "lat", "lon", 
            "risk_score", "risk_level", "contributing_factors", "last_updated"
        }

        for jnc in junctions:
            self.assertTrue(required_keys.issubset(jnc.keys()), f"Missing data contract keys in {jnc}")
            self.assertIsInstance(jnc["junction_id"], str)
            self.assertIsInstance(jnc["name"], str)
            self.assertIsInstance(jnc["lat"], float)
            self.assertIsInstance(jnc["lon"], float)
            
            if jnc["risk_score"] is not None:
                self.assertTrue(0.0 <= jnc["risk_score"] <= 100.0)
            
            if jnc["risk_level"] is not None:
                self.assertIn(jnc["risk_level"], ["LOW", "MEDIUM", "HIGH"])
            
            if jnc["contributing_factors"] is not None:
                self.assertIsInstance(jnc["contributing_factors"], list)
                for factor in jnc["contributing_factors"]:
                    self.assertIn("factor", factor)
                    self.assertIn("weight", factor)
                    self.assertTrue(0.0 <= factor["weight"] <= 1.0)

    def test_risk_score_bounds_and_explainability(self):
        """Verify that calculated risk scores fall within 0-100 and weights sum to ~1.0."""
        engine = ExplainableRiskEngine()
        result = engine.compute_junction_risk("JNC-BLR-001", vision_risk_score=75.0, weather_condition="Heavy Rain")
        
        score = result["risk_score"]
        factors = result["contributing_factors"]

        self.assertTrue(0.0 <= score <= 100.0, f"Calculated risk score {score} out of 0-100 bounds.")
        
        total_weight = sum(f["weight"] for f in factors)
        self.assertAlmostEqual(total_weight, 1.0, delta=0.05, msg=f"Factor weights should sum to approx 1.0, got {total_weight}")

    def test_historical_dataset_parser(self):
        """Verify historical dataset generation and metrics computation."""
        score, metrics = compute_historical_risk_score("JNC-BLR-001")
        self.assertTrue(0.0 <= score <= 100.0)
        self.assertIn("total_accidents", metrics)
        self.assertIn("fatalities", metrics)
        self.assertGreater(metrics["total_accidents"], 0)

if __name__ == "__main__":
    unittest.main()
