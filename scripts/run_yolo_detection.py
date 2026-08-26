#!/usr/bin/env python3
"""
CLI Runner for JunctionGuard AI YOLOv8 Detection Layer.
Runs video frame extraction and vehicle/pedestrian detection over video files
and outputs structured JSON and CSV detection metrics.
"""

import os
import sys
import argparse
import glob

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.vision.video_processor import VideoTrafficDetector

def main():
    parser = argparse.ArgumentParser(description="JunctionGuard AI - YOLOv8 Traffic Detection Runner")
    parser.add_argument(
        "--video",
        type=str,
        default="data/sample_videos",
        help="Path to input video file or directory containing video files."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/output",
        help="Directory to save JSON and CSV reports."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Frame extraction sampling interval in seconds (default: 0.5s)."
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="YOLO detection confidence threshold (default: 0.25)."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        help="YOLO model weights file path (default: yolov8n.pt)."
    )
    parser.add_argument(
        "--no-sample-img",
        action="store_true",
        help="Disable saving sample annotated JPEG frame images."
    )

    args = parser.parse_args()

    video_files = []
    if os.path.isfile(args.video):
        video_files.append(args.video)
    elif os.path.isdir(args.video):
        extensions = ("*.mp4", "*.avi", "*.mov", "*.mkv")
        for ext in extensions:
            video_files.extend(glob.glob(os.path.join(args.video, ext)))
            video_files.extend(glob.glob(os.path.join(args.video, ext.upper())))
    else:
        print(f"Error: Target path '{args.video}' does not exist.")
        sys.exit(1)

    if not video_files:
        print(f"No video files found at '{args.video}'.")
        sys.exit(1)

    print("=" * 65)
    print(" JunctionGuard AI - YOLOv8 Traffic Detection Layer")
    print(f" Model Weights : {args.model}")
    print(f" Confidence     : {args.conf}")
    print(f" Sampling       : Every {args.interval}s")
    print(f" Output Dir     : {args.output_dir}")
    print(f" Videos Found   : {len(video_files)}")
    print("=" * 65)

    detector = VideoTrafficDetector(model_weights=args.model, conf_threshold=args.conf)

    results = []
    for vid_path in sorted(video_files):
        print(f"\n[Processing Video] -> {os.path.basename(vid_path)}")
        res = detector.process_video(
            video_path=vid_path,
            output_dir=args.output_dir,
            interval_sec=args.interval,
            save_annotated_sample=not args.no_sample_img
        )
        results.append(res)

    print("\n" + "=" * 65)
    print(" SUMMARY OF DETECTION RUNS")
    print("=" * 65)
    for r in results:
        print(f" • {r['video_name']}:")
        print(f"   - Duration: {r['duration_sec']}s | Sampled Frames: {r['sampled_frames_count']}")
        print(f"   - Avg Vehicles/Frame: {r['avg_vehicles_per_frame']}")
        print(f"   - Avg 2-Wheeler Share: {r['avg_two_wheeler_share_pct']}%")
        print(f"   - JSON Report: {r['json_path']}")
        print(f"   - CSV Report : {r['csv_path']}")
        if r.get('sample_img_path'):
            print(f"   - Sample Image: {r['sample_img_path']}")

    print("\nYOLO Detection Layer execution complete successfully!")

if __name__ == "__main__":
    main()
