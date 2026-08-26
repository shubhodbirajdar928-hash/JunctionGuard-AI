"""
Video Frame Extraction & Detection Processor for JunctionGuard AI.
Processes video files using OpenCV at fixed time intervals (e.g., every 0.5s),
runs YOLOv8 object detection, and outputs structured JSON, CSV, and annotated video clips.
"""

import os
import cv2
import json
import csv
import pandas as pd
from typing import Dict, Any, List, Optional
from src.vision.detector import TrafficDetector

class VideoTrafficDetector:
    """
    Extracts frames from video files at specified fixed time intervals,
    runs YOLOv8 vehicle/pedestrian detection, and exports JSON/CSV reports.
    Includes robust error handling for corrupt or too-short videos.
    """
    def __init__(self, model_weights: str = "yolov8n.pt", conf_threshold: float = 0.25):
        self.detector = TrafficDetector(model_weights=model_weights)
        self.conf_threshold = conf_threshold

    def process_video(
        self,
        video_path: str,
        output_dir: str = "data/output",
        interval_sec: float = 0.5,
        save_annotated_sample: bool = True,
        save_annotated_video: bool = False,
        min_duration_sec: float = 1.0,
        max_sampled_frames: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Processes a video file, extracting frames every `interval_sec` seconds.

        Returns metadata dict with status 'success' or 'error'.
        """
        if not os.path.exists(video_path):
            return {
                "status": "error",
                "error": f"Video file not found at: {video_path}",
                "video_name": os.path.splitext(os.path.basename(video_path))[0]
            }

        os.makedirs(output_dir, exist_ok=True)
        video_name = os.path.splitext(os.path.basename(video_path))[0]

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {
                    "status": "error",
                    "error": f"Could not open video file (corrupt header or invalid codec): {video_path}",
                    "video_name": video_name
                }

            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0 or np_isnan(fps):
                fps = 30.0

            total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_duration_sec = total_video_frames / fps if fps > 0 else 0.0

            # Error handling for corrupt/empty or too-short videos
            if total_video_frames <= 0 or video_duration_sec < min_duration_sec:
                cap.release()
                return {
                    "status": "error",
                    "error": f"Video clip is too short ({video_duration_sec:.2f}s) or corrupted (0 total frames). Minimum required: {min_duration_sec}s.",
                    "video_name": video_name,
                    "duration_sec": round(video_duration_sec, 2),
                    "total_video_frames": total_video_frames
                }

            step_frames = max(1, int(round(fps * interval_sec)))

            frame_results: List[Dict[str, Any]] = []
            summary_rows: List[Dict[str, Any]] = []

            curr_frame_idx = 0
            processed_sample_frame = None

            # Video writer setup if saving annotated video clip
            annotated_video_path = None
            video_writer = None
            if save_annotated_video:
                annotated_dir = os.path.join(output_dir, "annotated")
                os.makedirs(annotated_dir, exist_ok=True)
                annotated_video_path = os.path.join(annotated_dir, f"{video_name}_annotated.mp4")

                frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if frame_w > 0 and frame_h > 0:
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    target_fps = min(30.0, fps / step_frames) if step_frames > 0 else 10.0
                    video_writer = cv2.VideoWriter(annotated_video_path, fourcc, target_fps, (frame_w, frame_h))

            print(f"[VideoTrafficDetector] Processing {video_name} (FPS: {fps:.2f}, Duration: {video_duration_sec:.2f}s, Interval: {interval_sec}s -> step: {step_frames} frames)...")

            while cap.isOpened():
                if max_sampled_frames is not None and len(frame_results) >= max_sampled_frames:
                    break

                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if curr_frame_idx % step_frames == 0:
                    timestamp_sec = round(curr_frame_idx / fps, 2)

                    # Process frame using YOLO detector
                    annotated_frame, metrics = self.detector.process_frame(
                        frame.copy(),
                        conf_threshold=self.conf_threshold
                    )

                    if processed_sample_frame is None:
                        processed_sample_frame = annotated_frame

                    if video_writer is not None:
                        video_writer.write(annotated_frame)

                    counts = metrics["counts"]
                    total_v = metrics["total_vehicles"]
                    two_w_share = metrics["two_wheeler_share_pct"]
                    ped_count = metrics["pedestrian_count"]
                    detections = metrics["raw_detections"]

                    # JSON frame payload
                    frame_entry = {
                        "frame_index": curr_frame_idx,
                        "timestamp_sec": timestamp_sec,
                        "counts": counts,
                        "total_vehicles": total_v,
                        "two_wheeler_share_pct": two_w_share,
                        "pedestrian_count": ped_count,
                        "detection_count": len(detections),
                        "detections": detections
                    }
                    frame_results.append(frame_entry)

                    # CSV summary row
                    summary_rows.append({
                        "frame_index": curr_frame_idx,
                        "timestamp_sec": timestamp_sec,
                        "car": counts["car"],
                        "motorcycle": counts["motorcycle"],
                        "bus": counts["bus"],
                        "truck": counts["truck"],
                        "pedestrian": ped_count,
                        "total_vehicles": total_v,
                        "two_wheeler_share_pct": two_w_share,
                        "detection_count": len(detections)
                    })

                curr_frame_idx += 1

            cap.release()
            if video_writer is not None:
                video_writer.release()

            if not frame_results:
                return {
                    "status": "error",
                    "error": f"No valid frames could be sampled from video file: {video_path}",
                    "video_name": video_name
                }

            # Save JSON output
            json_path = os.path.join(output_dir, f"{video_name}_detections.json")
            report_data = {
                "video_name": video_name,
                "fps": round(fps, 2),
                "interval_sec": interval_sec,
                "total_video_frames": total_video_frames,
                "duration_sec": round(video_duration_sec, 2),
                "sampled_frames_count": len(frame_results),
                "frames": frame_results
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)

            # Save CSV output
            csv_path = os.path.join(output_dir, f"{video_name}_summary.csv")
            df_summary = pd.DataFrame(summary_rows)
            df_summary.to_csv(csv_path, index=False)

            # Save sample annotated frame image if requested
            sample_img_path = None
            if save_annotated_sample and processed_sample_frame is not None:
                sample_img_path = os.path.join(output_dir, f"{video_name}_sample_frame.jpg")
                cv2.imwrite(sample_img_path, processed_sample_frame)

            avg_vehicles = round(df_summary["total_vehicles"].mean(), 1) if not df_summary.empty else 0.0
            avg_2w_share = round(df_summary["two_wheeler_share_pct"].mean(), 1) if not df_summary.empty else 0.0

            print(f"[VideoTrafficDetector] Completed {video_name}: {len(frame_results)} frames sampled. Output saved to {json_path} and {csv_path}")

            return {
                "status": "success",
                "video_name": video_name,
                "duration_sec": round(video_duration_sec, 2),
                "sampled_frames_count": len(frame_results),
                "json_path": json_path,
                "csv_path": csv_path,
                "sample_img_path": sample_img_path,
                "annotated_video_path": annotated_video_path,
                "avg_vehicles_per_frame": avg_vehicles,
                "avg_two_wheeler_share_pct": avg_2w_share
            }

        except Exception as ex:
            return {
                "status": "error",
                "error": f"Unexpected error processing video: {str(ex)}",
                "video_name": video_name
            }

def np_isnan(val):
    """Helper to safely check if val is NaN."""
    try:
        import numpy as np
        return np.isnan(val)
    except Exception:
        return False
