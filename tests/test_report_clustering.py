"""
Unit and integration tests for JunctionGuard AI's Citizen Report Clustering feature.
Tests:
1. Rolling 30-day time window filtering.
2. Anti-abuse 10-minute deduplication for same reporter.
3. Evidence weighting: text (1 pt), photo (2 pts), video (3 pts).
4. Score normalization with 10+ points = 100 cap.
5. Contributing factors formatting: 'Citizen Reports' with weight in [0, 1] summing to 1.0.
6. Threshold elevation: Crossing into HIGH risk purely from report clustering.
7. Immediate recalculation on report submission.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.risk_engine import (
    compute_citizen_report_cluster,
    classify_report_media,
    calculate_junction_risk_score,
    ExplainableRiskEngine,
    get_citizen_cluster_stats
)
from src.database import (
    init_db,
    add_citizen_report,
    fetch_junction_by_id,
    save_risk_score,
    get_db_connection
)

class TestReportClustering(unittest.TestCase):

    def setUp(self):
        init_db()
        self.ref_now = datetime(2026, 8, 27, 12, 0, 0)

    def test_evidence_weighting(self):
        """Verify text=1pt, photo=2pts, video=3pts, and correct summation."""
        reports = [
            {
                "report_id": "REP-1",
                "reporter_name": "Citizen A",
                "media_type": "text",
                "timestamp": "2026-08-20 10:00:00"
            },
            {
                "report_id": "REP-2",
                "reporter_name": "Citizen B",
                "media_type": "photo",
                "media_url": "https://supabase.co/pothole.jpg",
                "timestamp": "2026-08-21 11:00:00"
            },
            {
                "report_id": "REP-3",
                "reporter_name": "Citizen C",
                "media_type": "video",
                "media_url": "https://supabase.co/nearmiss.mp4",
                "timestamp": "2026-08-22 12:00:00"
            }
        ]

        result = compute_citizen_report_cluster(reports, reference_time=self.ref_now)

        # 1 + 2 + 3 = 6 points
        self.assertEqual(result["cluster_size"], 3)
        self.assertEqual(result["text_count"], 1)
        self.assertEqual(result["photo_count"], 1)
        self.assertEqual(result["video_count"], 1)
        self.assertEqual(result["media_count"], 2)
        self.assertEqual(result["report_severity_score"], 6)
        # Normalized: (6 / 10.0) * 100 = 60.0
        self.assertAlmostEqual(result["normalized_score"], 60.0, places=1)
        self.assertIn("3 reports in last 30 days, 2 with photo/video evidence", result["summary_line"])

    def test_normalization_cap_at_10_points(self):
        """Verify report_severity_score caps at 100 for 10+ weighted points without skewing scale."""
        reports = []
        for i in range(15):
            reports.append({
                "report_id": f"REP-PHOTO-{i}",
                "reporter_name": f"Citizen {i}",
                "media_url": f"https://cdn.example.com/photo_{i}.png",
                "timestamp": "2026-08-20 10:00:00"
            })

        # 15 photos * 2 points = 30 points -> Capped at 100.0
        result = compute_citizen_report_cluster(reports, reference_time=self.ref_now)
        self.assertEqual(result["cluster_size"], 15)
        self.assertEqual(result["media_count"], 15)
        self.assertEqual(result["report_severity_score"], 30)
        self.assertEqual(result["normalized_score"], 100.0)

    def test_rolling_30_day_window_filtering(self):
        """Verify reports older than 30 days are excluded from the rolling cluster."""
        reports = [
            {
                "report_id": "REP-RECENT",
                "reporter_name": "Citizen Recent",
                "media_type": "photo",
                "timestamp": "2026-08-15 10:00:00"  # 12 days ago (< 30d)
            },
            {
                "report_id": "REP-OLD",
                "reporter_name": "Citizen Old",
                "media_type": "video",
                "timestamp": "2026-07-10 10:00:00"  # 48 days ago (> 30d)
            }
        ]

        result = compute_citizen_report_cluster(reports, window_days=30, reference_time=self.ref_now)
        self.assertEqual(result["cluster_size"], 1)
        self.assertEqual(result["media_count"], 1)
        self.assertEqual(result["photo_count"], 1)
        self.assertEqual(result["video_count"], 0)
        self.assertEqual(result["report_severity_score"], 2)
        self.assertEqual(result["normalized_score"], 20.0)

    def test_anti_abuse_deduplication_within_10_minutes(self):
        """
        Verify multiple reports from the same reporter within 10 minutes count as one,
        preserving highest evidence tier.
        """
        reports = [
            # Citizen Spammer submits 3 reports within 6 minutes
            {
                "report_id": "SPAM-1",
                "reporter_name": "Ravi Kumar",
                "media_type": "text",
                "timestamp": "2026-08-26 14:00:00"
            },
            {
                "report_id": "SPAM-2",
                "reporter_name": "ravi kumar",  # case insensitive
                "media_type": "photo",
                "media_url": "https://img.com/pothole.jpg",
                "timestamp": "2026-08-26 14:04:00"
            },
            {
                "report_id": "SPAM-3",
                "reporter_name": "  Ravi Kumar  ",
                "media_type": "text",
                "timestamp": "2026-08-26 14:06:00"
            },
            # Another reporter legitimately submits at the same time
            {
                "report_id": "LEGIT-1",
                "reporter_name": "Anita Desai",
                "media_type": "text",
                "timestamp": "2026-08-26 14:05:00"
            }
        ]

        result = compute_citizen_report_cluster(reports, dedupe_window_minutes=10, reference_time=self.ref_now)
        # Ravi Kumar's 3 reports become 1 report with photo (2 pts)
        # Anita Desai's 1 report remains 1 report with text (1 pt)
        # Total cluster size = 2
        self.assertEqual(result["cluster_size"], 2)
        self.assertEqual(result["photo_count"], 1)
        self.assertEqual(result["text_count"], 1)
        self.assertEqual(result["report_severity_score"], 3)
        self.assertEqual(result["normalized_score"], 30.0)

    def test_anti_abuse_reports_separated_by_more_than_10_minutes(self):
        """Verify reports from the same reporter separated by > 10 minutes count as distinct reports."""
        reports = [
            {
                "report_id": "VALID-1",
                "reporter_name": "Sunil V",
                "media_type": "photo",
                "media_url": "https://img.com/pic1.jpg",
                "timestamp": "2026-08-26 10:00:00"
            },
            {
                "report_id": "VALID-2",
                "reporter_name": "Sunil V",
                "media_type": "photo",
                "media_url": "https://img.com/pic2.jpg",
                "timestamp": "2026-08-26 10:25:00"  # 25 minutes later
            }
        ]

        result = compute_citizen_report_cluster(reports, dedupe_window_minutes=10, reference_time=self.ref_now)
        self.assertEqual(result["cluster_size"], 2)
        self.assertEqual(result["photo_count"], 2)
        self.assertEqual(result["report_severity_score"], 4)
        self.assertEqual(result["normalized_score"], 40.0)

    def test_risk_engine_contributing_factors_and_weights(self):
        """Verify 'Citizen Reports' appears in contributing_factors with valid weight summing to 1.0."""
        traffic_indicators = {"traffic_density": 15.0, "conflict_proxy": 2, "pedestrian_activity": 2.0}
        accident_history_score = 50.0
        reports = [
            {"report_id": "CR1", "reporter_name": "U1", "media_url": "photo.jpg", "timestamp": "2026-08-25 10:00:00"},
            {"report_id": "CR2", "reporter_name": "U2", "media_url": "video.mp4", "timestamp": "2026-08-25 11:00:00"},
            {"report_id": "CR3", "reporter_name": "U3", "media_type": "text", "timestamp": "2026-08-25 12:00:00"}
        ]

        result = calculate_junction_risk_score(
            traffic_indicators=traffic_indicators,
            accident_history_score=accident_history_score,
            citizen_reports=reports
        )

        factors = result["contributing_factors"]
        factor_names = [f["factor"] for f in factors]
        self.assertIn("Citizen Reports", factor_names)

        total_weight = sum(f["weight"] for f in factors)
        self.assertAlmostEqual(total_weight, 1.0, delta=0.02)

        cit_factor = next(f for f in factors if f["factor"] == "Citizen Reports")
        self.assertTrue(0.0 <= cit_factor["weight"] <= 1.0)
        self.assertGreater(cit_factor["weight"], 0.05)

    def test_junction_threshold_elevation_to_high_risk_and_map_halo(self):
        """
        Verify that adding clustered citizen reports can elevate a junction
        across the 70.0 HIGH risk threshold, triggering the HIGH risk level and alert behavior.
        """
        # Baseline junction near 61.6 (MEDIUM risk, < 70.0)
        traffic_indicators = {"traffic_density": 22.0, "conflict_proxy": 4, "pedestrian_activity": 4.0}
        accident_history_score = 85.0

        # With 0 citizen reports:
        medium_result = calculate_junction_risk_score(
            traffic_indicators=traffic_indicators,
            accident_history_score=accident_history_score,
            citizen_reports=[]
        )
        self.assertLess(medium_result["risk_score"], 70.0)
        self.assertEqual(medium_result["risk_level"], "MEDIUM")

        # Now add heavy clustered reports from distinct citizens (10+ weighted points -> citizen subscore = 100)
        clustered_reports = [
            {
                "report_id": f"HIGH-R{i}",
                "reporter_name": f"Citizen Reporter {i}",
                "media_url": f"https://supabase.co/pothole_{i}.jpg",
                "timestamp": f"2026-08-26 1{i}:00:00"
            }
            for i in range(5)  # 5 photos * 2 pts = 10 pts -> 100 score
        ]

        high_result = calculate_junction_risk_score(
            traffic_indicators=traffic_indicators,
            accident_history_score=accident_history_score,
            citizen_reports=clustered_reports
        )
        # Boosting by 15 points elevates it past 70.0 (from 61.6 to 76.6)
        self.assertGreaterEqual(high_result["risk_score"], 70.0)
        self.assertEqual(high_result["risk_level"], "HIGH")

    def test_immediate_recalculation_on_add_citizen_report(self):
        """Verify that adding a citizen report immediately recalculates and updates junction risk score."""
        import uuid
        test_jnc_id = f"JNC-RECALC-{uuid.uuid4().hex[:6].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Seed test junction
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO junctions (junction_id, name, lat, lon, city, state, risk_score, risk_level, contributing_factors, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (test_jnc_id, "Test Recalc Junction", 12.9716, 77.5946, "Bengaluru", "Karnataka", 45.0, "MEDIUM", "[]", now_str))
        conn.commit()
        conn.close()

        engine = ExplainableRiskEngine()
        initial_score = engine.compute_junction_risk(test_jnc_id)["risk_score"]

        # Submit 3 citizen reports with photos
        for i in range(3):
            add_citizen_report(
                junction_id=test_jnc_id,
                reporter=f"Officer Test {i}",
                issue="Pothole / Road Hazard",
                severity=4,
                description=f"Hazard {i}",
                media_filename=f"evidence_{i}.jpg",
                media_url=f"https://supabase.co/evidence_{i}.jpg",
                media_type="photo"
            )

        # Trigger immediate calculation as performed by submission forms
        recalc_result = engine.compute_junction_risk(test_jnc_id)
        updated_jnc = fetch_junction_by_id(test_jnc_id)

        self.assertGreater(recalc_result["risk_score"], initial_score)
        self.assertAlmostEqual(updated_jnc["risk_score"], recalc_result["risk_score"], places=1)
        self.assertIn("Citizen Reports", [f["factor"] for f in updated_jnc["contributing_factors"]])

        # Verify cluster stats summary
        stats = get_citizen_cluster_stats(test_jnc_id)
        self.assertGreaterEqual(stats["cluster_size"], 3)
        self.assertIn("3 reports in last 30 days, 3 with photo/video evidence", stats["summary_line"])

if __name__ == "__main__":
    unittest.main()
