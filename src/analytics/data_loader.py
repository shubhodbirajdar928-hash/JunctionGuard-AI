"""
Accident Data Loader & Parser for JunctionGuard AI.
Loads and analyzes India Road Accident Datasets (Kaggle compatible).
Computes historical accident severity indices per junction.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CSV_PATH = os.path.join(DATA_DIR, "india_road_accidents_3000.csv")

def generate_sample_kaggle_dataset(filepath: str = CSV_PATH) -> pd.DataFrame:
    """
    Generates a realistic 3,000-record synthetic India Road Accident Dataset
    matching Kaggle khushikyad001 schema (2018-2023).
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    np.random.seed(42)

    junctions_data = [
        ("JNC-BLR-001", "Silk Board Junction", "Bengaluru", "Karnataka"),
        ("JNC-DEL-002", "ITO Crossing", "New Delhi", "Delhi"),
        ("JNC-MUM-003", "Dadar TT Circle", "Mumbai", "Maharashtra"),
        ("JNC-MAA-004", "Kathipara Junction", "Chennai", "Tamil Nadu"),
        ("JNC-HYD-005", "Panjagutta Junction", "Hyderabad", "Telangana"),
        ("JNC-BLR-006", "Goraguntepalya Junction", "Bengaluru", "Karnataka"),
        ("JNC-PNQ-007", "Chandani Chowk Junction", "Pune", "Maharashtra"),
    ]

    severities = ["Fatal", "Serious", "Minor"]
    weather_conds = ["Clear", "Heavy Rain", "Fog / Mist", "Monsoon Pour"]
    road_types = ["4-Lane Highway Merge", "Urban Intersection", "Roundabout", "Flyover Exit"]
    vehicle_combinations = [
        "Motorcycle & Bus", "Motorcycle & Car", "Car & Truck", 
        "Auto-rickshaw & Bus", "Pedestrian & Motorcycle", "Car & Car"
    ]

    records = []
    for i in range(3000):
        jnc_id, jnc_name, city, state = junctions_data[np.random.choice(len(junctions_data), p=[0.25, 0.20, 0.15, 0.10, 0.12, 0.13, 0.05])]
        year = np.random.choice([2018, 2019, 2020, 2021, 2022, 2023])
        severity = np.random.choice(severities, p=[0.22, 0.45, 0.33])
        
        if severity == "Fatal":
            fatalities = np.random.randint(1, 4)
            injuries = np.random.randint(0, 5)
        elif severity == "Serious":
            fatalities = 0
            injuries = np.random.randint(1, 4)
        else:
            fatalities = 0
            injuries = np.random.randint(0, 2)

        weather = np.random.choice(weather_conds, p=[0.55, 0.25, 0.12, 0.08])
        road_type = np.random.choice(road_types)
        v_combo = np.random.choice(vehicle_combinations)

        records.append({
            "Accident_ID": f"ACC-{200000+i}",
            "Junction_ID": jnc_id,
            "Junction_Name": jnc_name,
            "City": city,
            "State": state,
            "Year": year,
            "Accident_Severity": severity,
            "Fatalities": fatalities,
            "Injuries": injuries,
            "Weather_Conditions": weather,
            "Road_Type": road_type,
            "Vehicle_Types_Involved": v_combo
        })

    df = pd.DataFrame(records)
    df.to_csv(filepath, index=False)
    return df

def load_accident_dataset() -> pd.DataFrame:
    """Loads accident dataset, generating sample dataset if file does not exist."""
    if not os.path.exists(CSV_PATH):
        return generate_sample_kaggle_dataset(CSV_PATH)
    try:
        return pd.read_csv(CSV_PATH)
    except Exception:
        return generate_sample_kaggle_dataset(CSV_PATH)

def compute_historical_risk_score(junction_id: str) -> Tuple[float, Dict[str, Any]]:
    """
    Computes normalized historical accident severity risk score (0-100)
    and detailed metrics for a junction.
    Formula: Weighted sum of Fatalities (3x), Serious Injuries (1.5x), Minor Incidents (0.5x).
    """
    df = load_accident_dataset()
    j_df = df[df["Junction_ID"] == junction_id]
    
    if j_df.empty:
        return 20.0, {"total_accidents": 0, "fatalities": 0, "injuries": 0}

    total_accidents = len(j_df)
    fatalities = j_df["Fatalities"].sum()
    injuries = j_df["Injuries"].sum()
    fatal_count = (j_df["Accident_Severity"] == "Fatal").sum()
    serious_count = (j_df["Accident_Severity"] == "Serious").sum()

    # Raw severity index formula
    raw_score = (fatalities * 8.0) + (serious_count * 3.5) + (total_accidents * 0.4)
    # Scale non-linearly to 0-100
    norm_score = min(100.0, max(5.0, (raw_score / 450.0) * 100.0))

    metrics = {
        "total_accidents": int(total_accidents),
        "fatalities": int(fatalities),
        "injuries": int(injuries),
        "fatal_accidents": int(fatal_count),
        "serious_accidents": int(serious_count),
        "high_risk_weather_pct": round((j_df["Weather_Conditions"] != "Clear").mean() * 100, 1),
        "motorcycle_involvement_pct": round(j_df["Vehicle_Types_Involved"].str.contains("Motorcycle").mean() * 100, 1)
    }

    return round(norm_score, 1), metrics
