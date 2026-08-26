"""
Unit tests for the India Road Accident Dataset cleaning and historical risk score pipeline.
Verifies dataset loading, city-level aggregation, junction joining, 0-100 bounds, and CSV exports.
"""

import os
import sys
import unittest
import pandas as pd

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.data_loader import (
    load_accident_dataset,
    clean_accident_dataframe,
    aggregate_accident_history_by_city,
    compute_junction_accident_history_scores,
    compute_historical_risk_score,
    export_clean_accident_history_csvs,
    normalize_city_name,
    JUNCTION_SCORES_CSV,
    CITY_SUMMARY_CSV
)
from src.analytics.risk_engine import ExplainableRiskEngine

class TestAccidentHistoryPipeline(unittest.TestCase):

    def test_city_name_normalization(self):
        """Verify city normalization correctly handles aliases and formatting."""
        self.assertEqual(normalize_city_name("bangalore"), "Bengaluru")
        self.assertEqual(normalize_city_name("Bangalore"), "Bengaluru")
        self.assertEqual(normalize_city_name("BLR"), "Bengaluru")
        self.assertEqual(normalize_city_name("new delhi"), "New Delhi")
        self.assertEqual(normalize_city_name("bombay"), "Mumbai")
        self.assertEqual(normalize_city_name("madras"), "Chennai")
        self.assertEqual(normalize_city_name("kolhapur"), "Kolhapur")

    def test_clean_accident_dataframe(self):
        """Verify raw data cleaning handles dirty records, NaNs, and types."""
        raw_sample = pd.DataFrame([
            {"location": "bangalore", "deaths": 2, "injured": 3, "severity": "Fatal", "weather": "Heavy Rain"},
            {"location": "DELHI", "deaths": None, "injured": 1, "severity": "minor", "weather": None},
            {"location": "KOLHAPUR", "deaths": 0, "injured": 4, "severity": "Serious", "weather": "Fog"},
            {"location": None, "deaths": 0, "injured": 0, "severity": None, "weather": "Clear"}
        ])

        cleaned = clean_accident_dataframe(raw_sample)
        self.assertIn("City", cleaned.columns)
        self.assertIn("Fatalities", cleaned.columns)
        self.assertIn("Injuries", cleaned.columns)
        self.assertEqual(cleaned.loc[0, "City"], "Bengaluru")
        self.assertEqual(cleaned.loc[1, "City"], "New Delhi")
        self.assertEqual(cleaned.loc[2, "City"], "Kolhapur")
        self.assertEqual(cleaned.loc[3, "City"], "Unknown")
        self.assertEqual(int(cleaned.loc[0, "Fatalities"]), 2)
        self.assertEqual(int(cleaned.loc[1, "Fatalities"]), 0)

    def test_dataset_loading_and_shape(self):
        """Verify full accident dataset loads cleanly with >= 3000 records."""
        df = load_accident_dataset()
        self.assertGreaterEqual(len(df), 3000)
        self.assertIn("City", df.columns)
        self.assertIn("Accident_Severity", df.columns)
        self.assertIn("Fatalities", df.columns)
        self.assertIn("Injuries", df.columns)

    def test_city_level_aggregation(self):
        """Verify city-level aggregation produces valid metrics and scores between 0 and 100."""
        city_summary = aggregate_accident_history_by_city()
        self.assertGreater(len(city_summary), 0)
        
        required_cols = [
            "City", "State", "Total_Accidents", "Fatalities", "Injuries",
            "Fatal_Accidents", "Serious_Accidents", "Minor_Accidents",
            "City_Accident_Risk_Score"
        ]
        for col in required_cols:
            self.assertIn(col, city_summary.columns)

        for _, row in city_summary.iterrows():
            score = row["City_Accident_Risk_Score"]
            self.assertTrue(0.0 <= score <= 100.0, f"City score {score} out of bounds for {row['City']}")
            self.assertGreater(row["Total_Accidents"], 0)

    def test_junction_accident_history_scores_join(self):
        """Verify junction join assigns calibrated accident_history_score (0-100) to all demo junctions."""
        scored_df, scored_dict = compute_junction_accident_history_scores()
        
        # Test standard metro junctions exist
        metro_ids = ["JNC-BLR-001", "JNC-DEL-002", "JNC-MUM-003", "JNC-MAA-004", "JNC-HYD-005", "JNC-BLR-006", "JNC-PNQ-007"]
        for j_id in metro_ids:
            self.assertIn(j_id, scored_dict)
            score = scored_dict[j_id]["accident_history_score"]
            self.assertTrue(0.0 <= score <= 100.0, f"Junction score {score} out of bounds for {j_id}")

        # Test Kolhapur junctions exist
        kolhapur_ids = ["J001", "J002", "J003", "J004", "J005"]
        for k_id in kolhapur_ids:
            self.assertIn(k_id, scored_dict)
            score = scored_dict[k_id]["accident_history_score"]
            self.assertTrue(0.0 <= score <= 100.0, f"Kolhapur junction score {score} out of bounds for {k_id}")

    def test_compute_historical_risk_score_integration(self):
        """Verify compute_historical_risk_score returns tuple (score, metrics) for RiskEngine."""
        score, metrics = compute_historical_risk_score("JNC-BLR-001")
        self.assertTrue(0.0 <= score <= 100.0)
        self.assertIn("total_accidents", metrics)
        self.assertIn("fatalities", metrics)
        self.assertIn("injuries", metrics)
        self.assertIn("city", metrics)

        # Integration with ExplainableRiskEngine
        engine = ExplainableRiskEngine()
        result = engine.compute_junction_risk("JNC-BLR-001", vision_risk_score=70.0)
        self.assertTrue(0.0 <= result["risk_score"] <= 100.0)

    def test_csv_export_files(self):
        """Verify CSV export writes valid files with data."""
        j_path, c_path = export_clean_accident_history_csvs()
        self.assertTrue(os.path.exists(j_path))
        self.assertTrue(os.path.exists(c_path))
        
        j_df = pd.read_csv(j_path)
        c_df = pd.read_csv(c_path)
        self.assertGreater(len(j_df), 0)
        self.assertGreater(len(c_df), 0)
        self.assertIn("accident_history_score", j_df.columns)
        self.assertIn("City_Accident_Risk_Score", c_df.columns)

if __name__ == "__main__":
    unittest.main()
