"""
Traffic Indicators Calculation Engine for JunctionGuard AI.
Uses Pandas and NumPy to compute per-junction traffic density, speed/movement proxy,
pedestrian activity level, and conflict/near-miss proxy from YOLOv8 video frame logs.
"""

import os
import json
import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from src.supabase_client import insert_detection_indicator

class TrafficIndicatorCalculator:
    """
    Computes traffic metrics and conflict indicators from frame-by-frame YOLO detections.
    """
    def __init__(self, proximity_threshold_px: float = 50.0):
        self.proximity_threshold_px = proximity_threshold_px

    def compute_from_json(
        self,
        json_path: str,
        junction_id: str,
        source_video: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Loads a detection JSON report file and calculates per-junction indicators.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON detection report not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        video_filename = source_video or data.get("video_name", "unknown_video.mp4")
        if not video_filename.endswith((".mp4", ".avi", ".mov", ".mkv")):
            video_filename += ".mp4"

        return self.compute_from_frames_data(
            frames=data.get("frames", []),
            junction_id=junction_id,
            source_video=video_filename
        )

    def compute_from_frames_data(
        self,
        frames: List[Dict[str, Any]],
        junction_id: str,
        source_video: str
    ) -> Dict[str, Any]:
        """
        Calculates indicators using Pandas and NumPy over frames data array.
        """
        if not frames:
            return {
                "junction_id": junction_id,
                "source_video": source_video,
                "traffic_density": 0.0,
                "speed_proxy": 0.0,
                "pedestrian_activity": 0.0,
                "conflict_proxy": 0,
                "total_frames_analyzed": 0
            }

        df_frames = pd.DataFrame(frames)

        # 1. Traffic Density: Average vehicle count per sampled frame
        if "total_vehicles" in df_frames.columns:
            traffic_density = float(np.mean(df_frames["total_vehicles"]))
        else:
            traffic_density = 0.0

        # 2. Pedestrian Activity Level: Average pedestrian count per frame
        if "pedestrian_count" in df_frames.columns:
            pedestrian_activity = float(np.mean(df_frames["pedestrian_count"]))
        else:
            pedestrian_activity = 0.0

        # 3. Conflict / Near-Miss Proxy & 4. Speed / Movement Proxy calculation
        total_conflicts = 0
        speed_velocities: List[float] = []

        for i in range(len(frames)):
            f_curr = frames[i]
            dets_curr = f_curr.get("detections", [])

            # Compute conflicts in current frame using NumPy vectorization
            frame_conflicts = self._count_frame_conflicts(dets_curr)
            total_conflicts += frame_conflicts

            # Compute movement/speed proxy across consecutive frames
            if i > 0:
                f_prev = frames[i - 1]
                dt = f_curr.get("timestamp_sec", 0.0) - f_prev.get("timestamp_sec", 0.0)
                if dt <= 0:
                    dt = 0.5  # default fallback interval

                frame_speed = self._calculate_consecutive_frame_speed(
                    f_prev.get("detections", []),
                    dets_curr,
                    dt=dt
                )
                if frame_speed is not None:
                    speed_velocities.append(frame_speed)

        # Speed proxy average in px/second
        speed_proxy = float(np.mean(speed_velocities)) if speed_velocities else 0.0

        return {
            "junction_id": junction_id,
            "source_video": source_video,
            "traffic_density": round(traffic_density, 4),
            "speed_proxy": round(speed_proxy, 4),
            "pedestrian_activity": round(pedestrian_activity, 4),
            "conflict_proxy": int(total_conflicts),
            "total_frames_analyzed": len(frames)
        }

    def _count_frame_conflicts(self, detections: List[Dict[str, Any]]) -> int:
        """
        Uses NumPy distance matrices to identify vehicles and pedestrians within threshold distance.
        """
        if len(detections) < 2:
            return 0

        # Extract centroids and categories
        veh_centroids = []
        ped_centroids = []

        for d in detections:
            bbox = d.get("bbox", [0, 0, 0, 0])
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0
            cls = d.get("class", "")

            if cls == "pedestrian":
                ped_centroids.append([cx, cy])
            elif cls in ["car", "motorcycle", "bus", "truck"]:
                veh_centroids.append([cx, cy])

        conflicts = 0

        # Vehicle vs Pedestrian conflicts
        if veh_centroids and ped_centroids:
            V = np.array(veh_centroids)  # shape (N, 2)
            P = np.array(ped_centroids)  # shape (M, 2)
            # Calculate pairwise Euclidean distance matrix
            dist_matrix = np.linalg.norm(V[:, np.newaxis, :] - P[np.newaxis, :, :], axis=2)
            conflicts += int(np.sum(dist_matrix <= self.proximity_threshold_px))

        # Vehicle vs Vehicle tight proximity conflicts (e.g. 2-wheeler weaving close to heavy vehicle)
        if len(veh_centroids) >= 2:
            V = np.array(veh_centroids)
            dist_matrix_vv = np.linalg.norm(V[:, np.newaxis, :] - V[np.newaxis, :, :], axis=2)
            # Ignore self-distance on diagonal
            np.fill_diagonal(dist_matrix_vv, np.inf)
            # Count unique pairs (upper triangle)
            vv_conflicts = np.sum(np.triu(dist_matrix_vv <= (self.proximity_threshold_px * 0.7)))
            conflicts += int(vv_conflicts)

        return conflicts

    def _calculate_consecutive_frame_speed(
        self,
        prev_detections: List[Dict[str, Any]],
        curr_detections: List[Dict[str, Any]],
        dt: float
    ) -> Optional[float]:
        """
        Calculates centroid position change of matching object classes between consecutive frames.
        """
        if not prev_detections or not curr_detections or dt <= 0:
            return None

        displacements: List[float] = []

        # Group centroids by class
        prev_by_class: Dict[str, List[Tuple[float, float]]] = {}
        for d in prev_detections:
            cls = d.get("class", "unknown")
            bbox = d.get("bbox", [0, 0, 0, 0])
            cx, cy = (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0
            prev_by_class.setdefault(cls, []).append((cx, cy))

        curr_by_class: Dict[str, List[Tuple[float, float]]] = {}
        for d in curr_detections:
            cls = d.get("class", "unknown")
            bbox = d.get("bbox", [0, 0, 0, 0])
            cx, cy = (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0
            curr_by_class.setdefault(cls, []).append((cx, cy))

        # Match centroids for matching classes
        for cls in prev_by_class:
            if cls in curr_by_class:
                pts_prev = np.array(prev_by_class[cls])
                pts_curr = np.array(curr_by_class[cls])

                # Pairwise distance matrix between prev and curr centroids of same class
                dists = np.linalg.norm(pts_prev[:, np.newaxis, :] - pts_curr[np.newaxis, :, :], axis=2)
                # Find minimum distance per prev object
                min_dists = np.min(dists, axis=1)
                # Only count plausible displacements (< 200 pixels displacement between sampled frames)
                valid_dists = min_dists[min_dists < 200.0]
                if len(valid_dists) > 0:
                    displacements.extend(valid_dists.tolist())

        if not displacements:
            return None

        # Speed = average displacement / time delta (px/sec)
        avg_displacement = float(np.mean(displacements))
        return avg_displacement / dt

def process_and_upload_indicators(
    json_path: str,
    junction_id: str,
    source_video: Optional[str] = None,
    save_to_supabase: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to compute indicators from JSON file and upload directly to Supabase.
    """
    calculator = TrafficIndicatorCalculator()
    indicators = calculator.compute_from_json(
        json_path=json_path,
        junction_id=junction_id,
        source_video=source_video
    )

    if save_to_supabase:
        supabase_record = insert_detection_indicator(indicators)
        indicators["supabase_record"] = supabase_record
        print(f"[Supabase Upload] Successfully written indicator row for junction '{junction_id}'!")

    return indicators
