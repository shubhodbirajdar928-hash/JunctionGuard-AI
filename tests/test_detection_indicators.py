"""
Unit and Integration Tests for Traffic Indicator Calculations and Supabase Persistence.
"""

import os
import json
import pytest
import pandas as pd
import numpy as np
from src.analytics.indicator_engine import TrafficIndicatorCalculator
from src.supabase_client import get_supabase_client, insert_detection_indicator

def test_indicator_calculator_with_synthetic_frames():
    calculator = TrafficIndicatorCalculator(proximity_threshold_px=50.0)

    # Create synthetic frame detections
    synthetic_frames = [
        {
            "frame_index": 0,
            "timestamp_sec": 0.0,
            "counts": {"car": 2, "motorcycle": 1, "bus": 0, "truck": 0, "pedestrian": 2},
            "total_vehicles": 3,
            "two_wheeler_share_pct": 33.3,
            "pedestrian_count": 2,
            "detections": [
                {"class": "car", "confidence": 0.85, "bbox": [100, 100, 180, 180]},
                {"class": "car", "confidence": 0.90, "bbox": [300, 300, 380, 380]},
                {"class": "motorcycle", "confidence": 0.80, "bbox": [120, 110, 150, 150]},  # Conflict with car 1 (dist < 50px)
                {"class": "pedestrian", "confidence": 0.75, "bbox": [110, 105, 130, 140]},  # Conflict with car 1 & motorcycle
                {"class": "pedestrian", "confidence": 0.88, "bbox": [500, 500, 520, 540]}
            ]
        },
        {
            "frame_index": 12,
            "timestamp_sec": 0.5,
            "counts": {"car": 2, "motorcycle": 1, "bus": 0, "truck": 0, "pedestrian": 0},
            "total_vehicles": 3,
            "two_wheeler_share_pct": 33.3,
            "pedestrian_count": 0,
            "detections": [
                {"class": "car", "confidence": 0.85, "bbox": [110, 110, 190, 190]},  # Displaced by (10, 10) -> ~14.14px / 0.5s = 28.28 px/s
                {"class": "car", "confidence": 0.90, "bbox": [310, 310, 390, 390]},  # Displaced by (10, 10)
                {"class": "motorcycle", "confidence": 0.80, "bbox": [130, 120, 160, 160]}
            ]
        }
    ]

    res = calculator.compute_from_frames_data(
        frames=synthetic_frames,
        junction_id="J001",
        source_video="test_video.mp4"
    )

    assert res["junction_id"] == "J001"
    assert res["source_video"] == "test_video.mp4"
    assert res["traffic_density"] == 3.0  # (3 + 3) / 2
    assert res["pedestrian_activity"] == 1.0  # (2 + 0) / 2
    assert res["conflict_proxy"] > 0
    assert res["speed_proxy"] > 0.0

def test_supabase_client_fetch():
    client = get_supabase_client()
    res = client.table("junctions").select("*").limit(1).execute()
    assert res.data is not None
    assert len(res.data) > 0
