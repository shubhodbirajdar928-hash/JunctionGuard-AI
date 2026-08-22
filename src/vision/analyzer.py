"""
Traffic Density & Conflict Risk Analyzer for JunctionGuard AI.
Calculates near-miss proximity scores, congestion indices, and vision-based risk metrics.
"""

import math
from typing import Dict, Any, List

class TrafficVisionAnalyzer:
    """
    Analyzes spatial density of detected vehicles, calculates bounding box proximity
    (near-miss index), and outputs a 0-100 Vision Risk Score.
    """

    def calculate_near_miss_index(self, detections: List[Dict[str, Any]]) -> int:
        """
        Calculates near-miss conflicts based on bounding box centroids proximity.
        Indian intersections feature high two-wheeler weaving close to heavy vehicles.
        """
        if len(detections) < 2:
            return 0

        centroids = []
        for d in detections:
            bbox = d.get("bbox", [0, 0, 0, 0])
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0
            centroids.append((cx, cy, d.get("class", "car")))

        near_misses = 0
        threshold_dist = 45.0  # Pixel proximity threshold for potential conflict zone

        for i in range(len(centroids)):
            for j in range(i + 1, len(centroids)):
                c1, c2 = centroids[i], centroids[j]
                dist = math.hypot(c1[0] - c2[0], c1[1] - c2[1])
                if dist < threshold_dist:
                    # Higher risk if pedestrian or motorcycle involved
                    if "pedestrian" in (c1[2], c2[2]) or "motorcycle" in (c1[2], c2[2]):
                        near_misses += 2
                    else:
                        near_misses += 1

        return near_misses

    def compute_vision_risk_score(self, metrics: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Computes 0-100 Vision Risk Score from real-time video analytics.
        Formula factors:
        - Vehicle Density & Congestion (40%)
        - Near-miss conflicts index (35%)
        - High motorcycle ratio risk factor (15%)
        - Vulnerable pedestrian exposure (10%)
        """
        total_v = metrics.get("total_vehicles", 0)
        two_w_share = metrics.get("two_wheeler_share_pct", 0.0)
        peds = metrics.get("pedestrian_count", 0)
        detections = metrics.get("raw_detections", [])

        # 1. Congestion Score (0-100)
        congestion_score = min(100.0, (total_v / 40.0) * 100.0)

        # 2. Near-miss count & score
        near_miss_count = self.calculate_near_miss_index(detections)
        near_miss_score = min(100.0, near_miss_count * 12.5)

        # 3. Two-wheeler density risk (high weaving factor)
        two_w_risk = min(100.0, (two_w_share / 60.0) * 100.0)

        # 4. Pedestrian hazard exposure
        ped_exposure = min(100.0, peds * 18.0)

        # Composite Vision Risk Formula
        vision_risk = (
            (congestion_score * 0.40) +
            (near_miss_score * 0.35) +
            (two_w_risk * 0.15) +
            (ped_exposure * 0.10)
        )

        vision_risk = round(max(0.0, min(100.0, vision_risk)), 1)

        summary = {
            "vision_risk_score": vision_risk,
            "congestion_score": round(congestion_score, 1),
            "near_miss_count": near_miss_count,
            "two_wheeler_share_pct": two_w_share,
            "pedestrian_count": peds
        }

        return vision_risk, summary
