"""
CCTV Video Stream Processor for JunctionGuard AI.
Processes video streams or generates animated junction CCTV simulation frames.
"""

import cv2
import numpy as np
from typing import Generator, Tuple, Dict, Any
from src.vision.detector import TrafficDetector
from src.vision.analyzer import TrafficVisionAnalyzer

class StreamProcessor:
    def __init__(self, video_path: str = None):
        self.video_path = video_path
        self.detector = TrafficDetector()
        self.analyzer = TrafficVisionAnalyzer()

    def generate_simulated_frame(self, frame_idx: int) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Generates a realistic animated CCTV simulation frame of an Indian junction
        when external CCTV video files are not provided.
        """
        width, height = 800, 500
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Draw intersection roads (dark asphalt)
        frame[150:350, :] = (45, 45, 45) # Horizontal main road
        frame[:, 300:500] = (45, 45, 45) # Vertical cross road

        # Draw lane markings (dashed yellow & white lines)
        cv2.line(frame, (0, 250), (800, 250), (0, 255, 255), 2)
        cv2.line(frame, (400, 0), (400, 500), (0, 255, 255), 2)

        # Overlay CCTV Timestamp & Junction Title
        cv2.putText(frame, "LIVE CCTV FEED: SILK BOARD JUNCTION (CAM-04)", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"REC [LIVE] Frame: {frame_idx:05d}", (580, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

        # Run detection and analysis
        processed_frame, metrics = self.detector.process_frame(frame)
        vision_risk, summary = self.analyzer.compute_vision_risk_score(metrics)
        metrics.update(summary)

        # Overlay real-time vision metrics HUD on frame
        hud_bg = processed_frame[400:490, 15:350].copy()
        cv2.rectangle(processed_frame, (15, 400), (350, 490), (10, 10, 10), -1)
        cv2.putText(processed_frame, f"Vision Risk Index: {vision_risk:.1f}/100", (25, 425),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 2)
        cv2.putText(processed_frame, f"Vehicles: {metrics['total_vehicles']} | 2-Wheelers: {metrics['two_wheeler_share_pct']}%", (25, 450),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(processed_frame, f"Near-Miss Conflicts: {metrics['near_miss_count']}", (25, 475),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        return processed_frame, metrics
