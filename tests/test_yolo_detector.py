"""
Unit and Integration Tests for JunctionGuard AI YOLO Detection Layer.
"""

import os
import sys
import json
import unittest
import tempfile
import numpy as np
import cv2
import pandas as pd

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vision.detector import TrafficDetector
from src.vision.video_processor import VideoTrafficDetector

class TestYoloDetector(unittest.TestCase):

    def test_traffic_detector_single_frame(self):
        detector = TrafficDetector(model_weights="yolov8n.pt")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        annotated_frame, metrics = detector.process_frame(dummy_frame, conf_threshold=0.25)

        self.assertEqual(annotated_frame.shape, (480, 640, 3))
        self.assertIn("total_vehicles", metrics)
        self.assertIn("counts", metrics)
        self.assertIn("two_wheeler_share_pct", metrics)
        self.assertIn("pedestrian_count", metrics)
        self.assertIn("raw_detections", metrics)

        expected_classes = {"car", "motorcycle", "bus", "truck", "pedestrian"}
        self.assertEqual(set(metrics["counts"].keys()), expected_classes)

    def test_video_traffic_detector_processing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_video_path = os.path.join(tmp_dir, "test_synthetic.mp4")
            output_dir = os.path.join(tmp_dir, "output")

            fps = 30.0
            duration_sec = 1.0  # 1 second = 30 frames
            width, height = 320, 240
            total_frames = int(fps * duration_sec)

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(test_video_path, fourcc, fps, (width, height))

            for i in range(total_frames):
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                cv2.rectangle(frame, (50 + i * 2, 50), (100 + i * 2, 100), (255, 255, 255), -1)
                out.write(frame)
            out.release()

            video_detector = VideoTrafficDetector(model_weights="yolov8n.pt", conf_threshold=0.25)
            res = video_detector.process_video(
                video_path=test_video_path,
                output_dir=output_dir,
                interval_sec=0.5, 
                save_annotated_sample=True
            )

            self.assertTrue(os.path.exists(res["json_path"]))
            self.assertTrue(os.path.exists(res["csv_path"]))
            self.assertGreater(res["sampled_frames_count"], 0)

            # Verify JSON format
            with open(res["json_path"], "r", encoding="utf-8") as f:
                json_data = json.load(f)

            self.assertIn("frames", json_data)
            self.assertEqual(json_data["video_name"], "test_synthetic")
            self.assertEqual(len(json_data["frames"]), res["sampled_frames_count"])

            first_frame = json_data["frames"][0]
            self.assertIn("frame_index", first_frame)
            self.assertIn("timestamp_sec", first_frame)
            self.assertIn("counts", first_frame)
            self.assertIn("detections", first_frame)

if __name__ == "__main__":
    unittest.main()
