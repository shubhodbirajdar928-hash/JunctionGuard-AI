#!/usr/bin/env python3
"""
Master Pre-Processing Script for JunctionGuard AI Demo Videos.
Executes end-to-end processing (YOLOv8 frame sampling + indicator calculation + Supabase upload)
over 5 demo clips (including corrupt/short edge-case videos) to eliminate live inference latency during judging.
"""

import os
import sys
import glob
import json
import pandas as pd

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.vision.video_processor import VideoTrafficDetector
from src.analytics.indicator_engine import TrafficIndicatorCalculator
from src.supabase_client import insert_detection_indicator

# Junction Mapping for 5 Demo Videos (Seeded Indian Junctions in Kolhapur)
JUNCTION_VIDEO_MAP = [
    {"video": "indian_traffic_1.mp4", "junction_id": "J001", "name": "Shivaji Chowk"},
    {"video": "indian_traffic_2.mp4", "junction_id": "J002", "name": "Rajaram Corner"},
    {"video": "indian_traffic_3.mp4", "junction_id": "J003", "name": "Dabholkar Corner"},
    {"video": "indian_traffic_4.mp4", "junction_id": "J004", "name": "Cyber Chowk"},
    {"video": "corrupt_or_short_demo.mp4", "junction_id": "J005", "name": "Kawala Naka (Edge Case)"}
]

def ensure_corrupt_test_file(videos_dir: str):
    """Creates an intentionally corrupt/invalid video file for testing robust error handling."""
    corrupt_file = os.path.join(videos_dir, "corrupt_or_short_demo.mp4")
    if not os.path.exists(corrupt_file):
        with open(corrupt_file, "wb") as f:
            f.write(b"CORRUPT_INVALID_HEADER_DATA_12345")

def preprocess_all(
    videos_dir: str = "data/sample_videos",
    output_dir: str = "data/output",
    interval_sec: float = 0.5,
    save_to_supabase: bool = True
):
    print("=" * 80)
    print(" JunctionGuard AI - End-to-End Demo Video Pre-Processing & Supabase Upload")
    print(f" Source Directory : {videos_dir}")
    print(f" Output Directory : {output_dir}")
    print(f" Supabase Upload  : {save_to_supabase}")
    print("=" * 80)

    ensure_corrupt_test_file(videos_dir)

    detector = VideoTrafficDetector(model_weights="yolov8n.pt", conf_threshold=0.25)
    calculator = TrafficIndicatorCalculator(proximity_threshold_px=50.0)

    summary_records = []

    for entry in JUNCTION_VIDEO_MAP:
        v_name = entry["video"]
        jnc_id = entry["junction_id"]
        jnc_name = entry["name"]
        v_path = os.path.join(videos_dir, v_name)

        print(f"\n[Pre-Processing] Video: {v_name} | Target Junction: {jnc_id} ({jnc_name})")

        # Step 1: YOLO Detection & Video Sampling with robust error handling
        res_det = detector.process_video(
            video_path=v_path,
            output_dir=output_dir,
            interval_sec=interval_sec,
            save_annotated_sample=True,
            save_annotated_video=True,
            max_sampled_frames=100
        )

        if res_det.get("status") == "error":
            err_msg = res_det.get("error", "Unknown error")
            print(f"⚠️  [Handled Error] {err_msg}")
            summary_records.append({
                "Junction ID": jnc_id,
                "Junction Name": jnc_name,
                "Video File": v_name,
                "Status": "⚠️ Error Handled",
                "Traffic Density": "N/A",
                "Speed Proxy": "N/A",
                "Pedestrian Activity": "N/A",
                "Conflict Proxy": "N/A",
                "Supabase Written": False,
                "Note": err_msg[:45] + "..."
            })
            continue

        # Step 2: Calculate Traffic Indicators using Pandas & NumPy
        json_path = res_det["json_path"]
        indicators = calculator.compute_from_json(
            json_path=json_path,
            junction_id=jnc_id,
            source_video=v_name
        )

        # Step 3: Write indicators directly to Supabase
        supabase_written = False
        if save_to_supabase:
            try:
                db_record = insert_detection_indicator(indicators)
                supabase_written = bool(db_record)
                print(f"✅  [Supabase] Written record ID: {db_record.get('id', 'N/A')}")
            except Exception as e:
                print(f"❌  [Supabase Error] Could not write row: {e}")

        summary_records.append({
            "Junction ID": jnc_id,
            "Junction Name": jnc_name,
            "Video File": v_name,
            "Status": "✅ Processed",
            "Traffic Density": indicators["traffic_density"],
            "Speed Proxy": indicators["speed_proxy"],
            "Pedestrian Activity": indicators["pedestrian_activity"],
            "Conflict Proxy": indicators["conflict_proxy"],
            "Supabase Written": supabase_written,
            "Note": f"{indicators['total_frames_analyzed']} frames"
        })

    print("\n" + "=" * 80)
    print(" END-TO-END DEMO PRE-PROCESSING COMPLETED")
    print("=" * 80)

    df_summary = pd.DataFrame(summary_records)
    print(df_summary.to_string(index=False))
    print("=" * 80)

    # Save summary report artifact
    summary_path = os.path.join(output_dir, "demo_preprocessing_summary.csv")
    df_summary.to_csv(summary_path, index=False)
    print(f"Summary report saved to: {summary_path}")

if __name__ == "__main__":
    preprocess_all()
