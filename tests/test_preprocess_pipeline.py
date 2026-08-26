"""
Unit and Integration Tests for Demo Video Pre-Processing Pipeline & Error Handling.
"""

import os
import sys
import unittest
import tempfile
import numpy as np
import cv2

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vision.video_processor import VideoTrafficDetector

class TestPreprocessPipeline(unittest.TestCase):

    def test_corrupt_video_handling(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            detector = VideoTrafficDetector(model_weights="yolov8n.pt")
            
            # Create an invalid corrupt video file
            corrupt_file = os.path.join(tmp_dir, "corrupt_video.mp4")
            with open(corrupt_file, "wb") as f:
                f.write(b"NOT_A_REAL_VIDEO_HEADER_12345")

            res = detector.process_video(
                video_path=corrupt_file,
                output_dir=os.path.join(tmp_dir, "output")
            )

            self.assertEqual(res["status"], "error")
            self.assertIn("error", res)

    def test_too_short_video_handling(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            detector = VideoTrafficDetector(model_weights="yolov8n.pt")

            # Create a tiny 0.2 second video (6 frames at 30fps)
            short_video = os.path.join(tmp_dir, "short_video.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(short_video, fourcc, 30.0, (320, 240))
            for _ in range(6):
                out.write(np.zeros((240, 320, 3), dtype=np.uint8))
            out.release()

            res = detector.process_video(
                video_path=short_video,
                output_dir=os.path.join(tmp_dir, "output"),
                min_duration_sec=1.0
            )

            self.assertEqual(res["status"], "error")
            self.assertIn("too short", res["error"].lower())

    def test_annotated_video_recording(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            detector = VideoTrafficDetector(model_weights="yolov8n.pt")

            # Create a valid 1-second synthetic video (30 frames)
            valid_video = os.path.join(tmp_dir, "valid_video.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(valid_video, fourcc, 30.0, (320, 240))
            for i in range(30):
                frame = np.zeros((240, 320, 3), dtype=np.uint8)
                cv2.rectangle(frame, (50 + i * 2, 50), (100 + i * 2, 100), (255, 255, 255), -1)
                out.write(frame)
            out.release()

            res = detector.process_video(
                video_path=valid_video,
                output_dir=os.path.join(tmp_dir, "output"),
                interval_sec=0.5,
                save_annotated_video=True
            )

            self.assertEqual(res["status"], "success")
            self.assertIsNotNone(res["annotated_video_path"])
            self.assertTrue(os.path.exists(res["annotated_video_path"]))

if __name__ == "__main__":
    unittest.main()
