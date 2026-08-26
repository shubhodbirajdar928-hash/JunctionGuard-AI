#!/usr/bin/env python3
"""
CLI Utility for JunctionGuard AI Traffic Indicator Processing & Supabase Persistence.
Calculates traffic density, speed proxy, pedestrian activity level, and conflict proxy
from YOLO detection logs and writes records directly into Supabase 'detection_indicators' table.
"""

import os
import sys
import glob
import argparse
import pandas as pd

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics.indicator_engine import process_and_upload_indicators, TrafficIndicatorCalculator

def main():
    parser = argparse.ArgumentParser(description="JunctionGuard AI - Compute Traffic Indicators & Upload to Supabase")
    parser.add_argument(
        "--json-dir",
        type=str,
        default="data/output",
        help="Directory containing YOLO detection JSON files (default: data/output)."
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Path to a specific detection JSON report file."
    )
    parser.add_argument(
        "--junction-id",
        type=str,
        default="J001",
        help="Junction ID to associate with the processed video indicators (default: J001)."
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Dry run mode: calculate indicators without writing to Supabase."
    )

    args = parser.parse_args()

    json_files = []
    if args.json:
        if os.path.exists(args.json):
            json_files.append(args.json)
        else:
            print(f"Error: Specified JSON file '{args.json}' does not exist.")
            sys.exit(1)
    elif os.path.isdir(args.json_dir):
        json_files = glob.glob(os.path.join(args.json_dir, "*_detections.json"))

    if not json_files:
        print(f"No detection JSON files found in '{args.json_dir}'.")
        sys.exit(1)

    print("=" * 70)
    print(" JunctionGuard AI - Traffic Indicators & Supabase Persistence")
    print(f" Junction ID    : {args.junction_id}")
    print(f" Upload to DB   : {not args.no_upload}")
    print(f" JSON Files     : {len(json_files)}")
    print("=" * 70)

    results = []
    for j_path in sorted(json_files):
        print(f"\n[Processing Report] -> {os.path.basename(j_path)}")
        res = process_and_upload_indicators(
            json_path=j_path,
            junction_id=args.junction_id,
            save_to_supabase=not args.no_upload
        )
        results.append(res)

    print("\n" + "=" * 70)
    print(" COMPUTED INDICATORS SUMMARY")
    print("=" * 70)

    summary_table = []
    for r in results:
        summary_table.append({
            "Junction ID": r["junction_id"],
            "Source Video": r["source_video"],
            "Traffic Density": r["traffic_density"],
            "Speed Proxy (px/s)": r["speed_proxy"],
            "Pedestrian Activity": r["pedestrian_activity"],
            "Conflict Proxy": r["conflict_proxy"],
            "Frames": r["total_frames_analyzed"]
        })

    df_summary = pd.DataFrame(summary_table)
    print(df_summary.to_string(index=False))
    print("=" * 70)
    print("Processing complete successfully!")

if __name__ == "__main__":
    main()
