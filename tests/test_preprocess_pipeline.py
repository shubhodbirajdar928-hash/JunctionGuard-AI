"""
Unit and Integration Tests for Demo Video Pre-Processing Pipeline & Error Handling.
"""

import os
import pytest
import numpy as np
import cv2
from src.vision.video_processor import VideoTrafficDetector

def test_corrupt_video_handling(tmp_path):
    detector = VideoTrafficDetector(model_weights="yolov8n.pt")
    
    # Create an invalid corrupt video file
    corrupt_file = str(tmp_path / "corrupt_video.mp4")
    with open(corrupt_file, "wb") as f:
        f.write(b"NOT_A_REAL_VIDEO_HEADER_12345")

    res = detector.process_video(
        video_path=corrupt_file,
        output_dir=str(tmp_path / "output")
    )

    assert res["status"] == "error"
    assert "error" in res
    assert "Could not open" in res["error"] or "corrupt" in res["error"].lower()

def test_too_short_video_handling(tmp_path):
    detector = VideoTrafficDetector(model_weights="yolov8n.pt")

    # Create a tiny 0.2 second video (6 frames at 30fps)
    short_video = str(tmp_path / "short_video.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(short_video, fourcc, 30.0, (320, 240))
    for _ in range(6):
        out.write(np.zeros((240, 320, 3), dtype=np.uint8))
    out.release()

    res = detector.process_video(
        video_path=short_video,
        output_dir=str(tmp_path / "output"),
        min_duration_sec=1.0  # requires at least 1 second duration
    )

    assert res["status"] == "error"
    assert "too short" in res["error"].lower()

def test_annotated_video_recording(tmp_path):
    detector = VideoTrafficDetector(model_weights="yolov8n.pt")

    # Create a valid 2-second synthetic video
    valid_video = str(tmp_path / "valid_video.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(valid_video, fourcc, 30.0, (640, 480))
    for i in range(60):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (100 + i * 2, 100), (200 + i * 2, 200), (255, 255, 255), -1)
        out.write(frame)
    out.release()

    res = detector.process_video(
        video_path=valid_video,
        output_dir=str(tmp_path / "output"),
        interval_sec=0.5,
        save_annotated_video=True
    )

    assert res["status"] == "success"
    assert res["annotated_video_path"] is not None
    assert os.path.exists(res["annotated_video_path"])
