"""
CLI Script to Process & Clean India Road Accident Dataset.
Downloads/loads Kaggle dataset (khushikyad001/india-road-accident-dataset-predictive-analysis),
cleans and normalizes columns/cities, aggregates accident severity by city,
joins to demo junctions, and outputs clean CSV reports for the JunctionGuard AI risk engine.
"""

import os
import sys
import argparse
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from src.analytics.data_loader import (
    load_accident_dataset,
    aggregate_accident_history_by_city,
    compute_junction_accident_history_scores,
    export_clean_accident_history_csvs,
    JUNCTION_SCORES_CSV,
    CITY_SUMMARY_CSV
)

def try_download_kaggle_dataset(output_dir: str):
    """
    Attempts to download Kaggle dataset using kaggle CLI or kaggle API if installed and configured.
    """
    dataset_slug = "khushikyad001/india-road-accident-dataset-predictive-analysis"
    print(f"[*] Checking Kaggle API for dataset: {dataset_slug}...")
    try:
        import subprocess
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", dataset_slug, "-p", output_dir, "--unzip"],
            capture_output=True,
            text=True,
            timeout=20
        )
        if result.returncode == 0:
            print("[+] Successfully downloaded latest Kaggle dataset via CLI!")
            return True
        else:
            print(f"[!] Kaggle CLI note: {result.stderr.strip() or 'Kaggle credentials not configured in environment'}")
    except Exception as e:
        print(f"[!] Note on Kaggle download: {e}. Using deterministic Kaggle-schema compliant dataset.")
    return False

def main():
    parser = argparse.ArgumentParser(description="Process and clean India Road Accident Dataset for JunctionGuard AI.")
    parser.add_argument("--download", action="store_true", help="Attempt to download dataset from Kaggle")
    parser.add_argument("--export-only", action="store_true", help="Export clean CSVs and exit")
    args = parser.parse_args()

    print("======================================================================")
    print("[JunctionGuard AI] India Road Accident Predictive Dataset Pipeline")
    print("======================================================================")

    data_dir = os.path.join(PROJECT_ROOT, "data")
    if args.download:
        try_download_kaggle_dataset(data_dir)

    # 1. Load and clean raw accident data
    print("\n[1/4] Loading & Cleaning Accident Dataset...")
    df = load_accident_dataset()
    print(f"      Loaded {len(df):,} cleaned accident records across {df['City'].nunique()} Indian cities.")
    print(f"      Columns: {list(df.columns)}")

    # 2. Aggregate city-level severity & frequency
    print("\n[2/4] Aggregating Accident Severity & Frequency by City...")
    city_summary = aggregate_accident_history_by_city(df)
    print("\n" + city_summary.to_string(index=False))

    # 3. Join with demo junctions
    print("\n[3/4] Joining with Demo Junctions & Calculating accident_history_score (0-100)...")
    junction_scores_df, junction_dict = compute_junction_accident_history_scores(df)
    
    display_cols = ["junction_id", "junction_name", "city", "accident_history_score", "total_accidents", "fatalities", "injuries"]
    print("\n" + junction_scores_df[display_cols].to_string(index=False))

    # 4. Export Clean CSVs
    print("\n[4/4] Exporting Clean CSV Reports for Risk Engine...")
    j_csv, c_csv = export_clean_accident_history_csvs()
    print(f"      [+] Junction Accident History Scores: {j_csv}")
    print(f"      [+] City Accident Severity Summary:   {c_csv}")

    print("\n[SUCCESS] Pipeline execution finished successfully. Risk Engine is primed with clean scores!")

if __name__ == "__main__":
    main()
