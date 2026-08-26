"""
Unit and Integration Tests for JunctionGuard AI YOLO Detection Layer.
"""

import os
import json
import pytest
import numpy as np
import cv2
import pandas as pd
from src.vision.detector import TrafficDetector
from src.vision.video_processor import VideoTrafficDetector

def test_traffic_detector_single_frame():
    detector = TrafficDetector(model_weights="yolov8n.pt")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    annotated_frame, metrics = detector.process_frame(dummy_frame, conf_threshold=0.25)

    assert annotated_frame.shape == (480, 640, 3)
    assert "total_vehicles" in metrics
    assert "counts" in metrics
    assert "two_wheeler_share_pct" in metrics
    assert "pedestrian_count" in metrics
    assert "raw_detections" in metrics

    # Verify counts keys include all required target classes
    expected_classes = {"car", "motorcycle", "bus", "truck", "pedestrian"}
    assert set(metrics["counts"].keys()) == expected_classes

def test_video_traffic_detector_processing(tmp_path):
    # Create a small synthetic video for integration testing
    test_video_path = str(tmp_path / "test_synthetic.mp4")
    output_dir = str(tmp_path / "output")

    fps = 30.0
    duration_sec = 2.0  # 2 seconds = 60 frames
    width, height = 640, 480
    total_frames = int(fps * duration_sec)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(test_video_path, fourcc, fps, (width, height))

    for i in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Draw moving rectangle simulating vehicle motion
        cv2.rectangle(frame, (50 + i * 2, 100), (150 + i * 2, 200), (255, 255, 255), -1)
        out.write(frame)
    out.release()

    video_detector = VideoTrafficDetector(model_weights="yolov8n.pt", conf_threshold=0.25)
    res = video_detector.process_video(
        video_path=test_video_path,
        output_dir=output_dir,
        interval_sec=0.5, 
        save_annotated_sample=True
    )

    assert os.path.exists(res["json_path"])
    assert os.path.exists(res["csv_path"])
    assert res["sampled_frames_count"] > 0

    # Verify JSON format
    with open(res["json_path"], "r", encoding="utf-8") as f:
        json_data = json.load(f)

    assert "frames" in json_data
    assert json_data["video_name"] == "test_synthetic"
    assert len(json_data["frames"]) == res["sampled_frames_count"]

    first_frame = json_data["frames"][0]
    assert "frame_index" in first_frame
    assert "timestamp_sec" in first_frame
    assert "counts" in first_frame
    assert "detections" in first_frame

    # Verify CSV format
    df_csv = pd.read_csv(res["csv_path"])
    assert not df_csv.empty
    assert "motorcycle" in df_csv.columns
    assert "two_wheeler_share_pct" in df_csv.columns
    assert "total_vehicles" in df_csv.columns
