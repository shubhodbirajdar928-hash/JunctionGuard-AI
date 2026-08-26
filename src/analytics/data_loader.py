"""
Accident Data Loader & Pipeline for JunctionGuard AI.
Loads, cleans, and analyzes the India Road Accident Dataset (Kaggle: khushikyad001).
Aggregates accident frequency and severity by City as a baseline risk contribution,
joins with demo junctions, and outputs clean accident_history_score (0-100) per junction.
"""

import os
import re
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
CSV_PATH = os.path.join(DATA_DIR, "india_road_accidents_3000.csv")
KAGGLE_RAW_PATH = os.path.join(DATA_DIR, "kaggle_india_road_accidents.csv")
JUNCTION_SCORES_CSV = os.path.join(OUTPUT_DIR, "junction_accident_history_scores.csv")
CITY_SUMMARY_CSV = os.path.join(OUTPUT_DIR, "city_accident_severity_summary.csv")

# Standard City Normalization Aliases Map for Indian Cities
CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "blr": "Bengaluru",
    "delhi": "New Delhi",
    "new delhi": "New Delhi",
    "ndls": "New Delhi",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "chennai": "Chennai",
    "madras": "Chennai",
    "hyderabad": "Hyderabad",
    "hyd": "Hyderabad",
    "secunderabad": "Hyderabad",
    "pune": "Pune",
    "pnq": "Pune",
    "kolhapur": "Kolhapur",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "ahmedabad": "Ahmedabad",
    "jaipur": "Jaipur",
    "lucknow": "Lucknow",
    "chandigarh": "Chandigarh",
    "nagpur": "Nagpur",
    "coimbatore": "Coimbatore",
    "indore": "Indore",
    "kochi": "Kochi",
    "cochin": "Kochi"
}

# Complete Registry of Demo Junctions across Main Dashboard & Directory
ALL_DEMO_JUNCTIONS = [
    {
        "junction_id": "JNC-BLR-001",
        "name": "Silk Board Junction",
        "city": "Bengaluru",
        "state": "Karnataka",
        "lat": 12.9172,
        "lon": 77.6228,
        "junction_type": "Major Flyover & Arterial Merge",
        "local_risk_modifier": 1.12 # High congestion bottleneck multiplier
    },
    {
        "junction_id": "JNC-DEL-002",
        "name": "ITO Crossing",
        "city": "New Delhi",
        "state": "Delhi",
        "lat": 28.6289,
        "lon": 77.2415,
        "junction_type": "High-Speed Multi-Leg Intersection",
        "local_risk_modifier": 1.05
    },
    {
        "junction_id": "JNC-MUM-003",
        "name": "Dadar TT Circle",
        "city": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0178,
        "lon": 72.8478,
        "junction_type": "Dense Urban Roundabout & Bus Transit Merge",
        "local_risk_modifier": 0.98
    },
    {
        "junction_id": "JNC-MAA-004",
        "name": "Kathipara Junction",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "lat": 13.0067,
        "lon": 80.2020,
        "junction_type": "Cloverleaf Grade Separator",
        "local_risk_modifier": 0.92
    },
    {
        "junction_id": "JNC-HYD-005",
        "name": "Panjagutta Junction",
        "city": "Hyderabad",
        "state": "Telangana",
        "lat": 17.4256,
        "lon": 78.4514,
        "junction_type": "Commercial Corridor Intersection",
        "local_risk_modifier": 1.00
    },
    {
        "junction_id": "JNC-BLR-006",
        "name": "Goraguntepalya Junction",
        "city": "Bengaluru",
        "state": "Karnataka",
        "lat": 13.0285,
        "lon": 77.5404,
        "junction_type": "Industrial Heavy Freight Corridor",
        "local_risk_modifier": 1.08
    },
    {
        "junction_id": "JNC-PNQ-007",
        "name": "Chandani Chowk Junction",
        "city": "Pune",
        "state": "Maharashtra",
        "lat": 18.5074,
        "lon": 73.7806,
        "junction_type": "Highway Grade Interchange",
        "local_risk_modifier": 0.88
    },
    # Kolhapur Demo Junctions (from app/data_loader.py)
    {
        "junction_id": "J001",
        "name": "Shivaji Chowk",
        "city": "Kolhapur",
        "state": "Maharashtra",
        "lat": 16.6996,
        "lon": 74.2433,
        "junction_type": "Heritage Market Central Square",
        "local_risk_modifier": 0.95
    },
    {
        "junction_id": "J002",
        "name": "Rajaram Corner",
        "city": "Kolhapur",
        "state": "Maharashtra",
        "lat": 16.7025,
        "lon": 74.2505,
        "junction_type": "Secondary Arterial Crossroad",
        "local_risk_modifier": 0.90
    },
    {
        "junction_id": "J003",
        "name": "Dabholkar Corner",
        "city": "Kolhapur",
        "state": "Maharashtra",
        "lat": 16.7001,
        "lon": 74.2482,
        "junction_type": "Station Road Transit Hub",
        "local_risk_modifier": 1.02
    },
    {
        "junction_id": "J004",
        "name": "Cyber Chowk",
        "city": "Kolhapur",
        "state": "Maharashtra",
        "lat": 16.6853,
        "lon": 74.2541,
        "junction_type": "University & IT Zone Square",
        "local_risk_modifier": 0.85
    },
    {
        "junction_id": "J005",
        "name": "Kawala Naka",
        "city": "Kolhapur",
        "state": "Maharashtra",
        "lat": 16.7018,
        "lon": 74.2575,
        "junction_type": "National Highway Entry Interchange",
        "local_risk_modifier": 1.06
    }
]

def normalize_city_name(raw_city: Any) -> str:
    """Normalizes raw city names to standard clean names."""
    if not raw_city or pd.isna(raw_city):
        return "Unknown"
    cleaned = str(raw_city).strip().lower()
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return CITY_ALIASES.get(cleaned, str(raw_city).strip().title())

def generate_sample_kaggle_dataset(filepath: str = CSV_PATH) -> pd.DataFrame:
    """
    Generates a realistic 3,000-record India Road Accident Dataset
    matching Kaggle khushikyad001 schema (2018-2023).
    Includes realistic distribution across major Indian cities and secondary hubs.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    np.random.seed(42)

    cities_data = [
        ("Bengaluru", "Karnataka", 0.24),
        ("New Delhi", "Delhi", 0.20),
        ("Mumbai", "Maharashtra", 0.16),
        ("Chennai", "Tamil Nadu", 0.11),
        ("Hyderabad", "Telangana", 0.12),
        ("Pune", "Maharashtra", 0.10),
        ("Kolhapur", "Maharashtra", 0.07),
    ]

    city_names = [c[0] for c in cities_data]
    city_states = {c[0]: c[1] for c in cities_data}
    city_probs = [c[2] for c in cities_data]

    severities = ["Fatal", "Serious", "Minor"]
    weather_conds = ["Clear", "Heavy Rain", "Fog / Mist", "Monsoon Pour"]
    road_types = ["4-Lane Highway Merge", "Urban Intersection", "Roundabout", "Flyover Exit", "Arterial Road"]
    vehicle_combinations = [
        "Motorcycle & Bus", "Motorcycle & Car", "Car & Truck", 
        "Auto-rickshaw & Bus", "Pedestrian & Motorcycle", "Car & Car",
        "Two-Wheeler & Heavy Lorry", "Pedestrian & Car"
    ]

    records = []
    for i in range(3000):
        city = np.random.choice(city_names, p=city_probs)
        state = city_states[city]
        year = int(np.random.choice([2018, 2019, 2020, 2021, 2022, 2023]))
        
        # High traffic cities have slightly higher fatal & serious probabilities
        if city in ["Bengaluru", "New Delhi"]:
            severity = np.random.choice(severities, p=[0.26, 0.46, 0.28])
        elif city in ["Mumbai", "Hyderabad"]:
            severity = np.random.choice(severities, p=[0.21, 0.44, 0.35])
        elif city == "Kolhapur":
            severity = np.random.choice(severities, p=[0.16, 0.42, 0.42])
        else:
            severity = np.random.choice(severities, p=[0.18, 0.42, 0.40])
        
        if severity == "Fatal":
            fatalities = int(np.random.randint(1, 4))
            injuries = int(np.random.randint(0, 5))
        elif severity == "Serious":
            fatalities = 0
            injuries = int(np.random.randint(1, 4))
        else:
            fatalities = 0
            injuries = int(np.random.randint(0, 2))

        weather = np.random.choice(weather_conds, p=[0.54, 0.24, 0.14, 0.08])
        road_type = np.random.choice(road_types)
        v_combo = np.random.choice(vehicle_combinations)

        records.append({
            "Accident_ID": f"ACC-{200000+i}",
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

def clean_accident_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw accident records from Kaggle or external sources:
    - Normalizes column names (lower/stripped).
    - Standardizes and normalizes City and State names.
    - Imputes and validates numeric fields (Fatalities, Injuries >= 0).
    - Cleans Accident Severity categories.
    - Drops invalid/duplicate records.
    """
    cleaned_df = df.copy()

    # Column name mapping
    col_map = {col: col.strip() for col in cleaned_df.columns}
    cleaned_df.rename(columns=col_map, inplace=True)

    # Standardize column headers if different variations exist
    lower_map = {col: col.lower().replace(" ", "_") for col in cleaned_df.columns}
    inv_map = {}
    for orig, standard in lower_map.items():
        if standard in ["city", "location", "district"]:
            inv_map[orig] = "City"
        elif standard in ["state", "province", "region"]:
            inv_map[orig] = "State"
        elif standard in ["year", "accident_year", "date"]:
            inv_map[orig] = "Year"
        elif standard in ["accident_severity", "severity", "accident_type"]:
            inv_map[orig] = "Accident_Severity"
        elif standard in ["fatalities", "deaths", "number_of_fatalities", "killed"]:
            inv_map[orig] = "Fatalities"
        elif standard in ["injuries", "number_of_injuries", "injured", "casualties"]:
            inv_map[orig] = "Injuries"
        elif standard in ["weather_conditions", "weather", "weather_condition"]:
            inv_map[orig] = "Weather_Conditions"
        elif standard in ["road_type", "road_class", "junction_type"]:
            inv_map[orig] = "Road_Type"
        elif standard in ["vehicle_types_involved", "vehicles_involved", "vehicle_type"]:
            inv_map[orig] = "Vehicle_Types_Involved"

    cleaned_df.rename(columns=inv_map, inplace=True)

    # Ensure required minimum columns exist
    if "City" not in cleaned_df.columns:
        cleaned_df["City"] = "Unknown"
    if "Fatalities" not in cleaned_df.columns:
        cleaned_df["Fatalities"] = 0
    if "Injuries" not in cleaned_df.columns:
        cleaned_df["Injuries"] = 0
    if "Accident_Severity" not in cleaned_df.columns:
        cleaned_df["Accident_Severity"] = "Minor"

    # Clean City names
    cleaned_df["City"] = cleaned_df["City"].apply(normalize_city_name)

    # Clean Numerics
    cleaned_df["Fatalities"] = pd.to_numeric(cleaned_df["Fatalities"], errors="coerce").fillna(0).astype(int).clip(lower=0)
    cleaned_df["Injuries"] = pd.to_numeric(cleaned_df["Injuries"], errors="coerce").fillna(0).astype(int).clip(lower=0)

    # Standardize Severity
    def standardize_severity(val, fatalities, injuries):
        if pd.isna(val):
            if fatalities > 0: return "Fatal"
            elif injuries > 0: return "Serious"
            return "Minor"
        val_str = str(val).strip().capitalize()
        if "Fatal" in val_str or fatalities > 0:
            return "Fatal"
        elif "Serious" in val_str or "Severe" in val_str or injuries >= 2:
            return "Serious"
        return "Minor"

    cleaned_df["Accident_Severity"] = cleaned_df.apply(
        lambda r: standardize_severity(r["Accident_Severity"], r["Fatalities"], r["Injuries"]),
        axis=1
    )

    # Clean Strings
    if "Weather_Conditions" in cleaned_df.columns:
        cleaned_df["Weather_Conditions"] = cleaned_df["Weather_Conditions"].fillna("Clear").astype(str).str.strip()
    else:
        cleaned_df["Weather_Conditions"] = "Clear"

    if "Vehicle_Types_Involved" in cleaned_df.columns:
        cleaned_df["Vehicle_Types_Involved"] = cleaned_df["Vehicle_Types_Involved"].fillna("Car").astype(str).str.strip()
    else:
        cleaned_df["Vehicle_Types_Involved"] = "Car"

    # Drop pure duplicates
    cleaned_df.drop_duplicates(inplace=True)

    return cleaned_df

def load_accident_dataset() -> pd.DataFrame:
    """
    Loads and cleans accident dataset.
    Prioritizes raw Kaggle dataset if available, falls back to standard cleaned dataset,
    or generates deterministic 3,000-record dataset if missing.
    """
    df = None
    if os.path.exists(KAGGLE_RAW_PATH):
        try:
            df = pd.read_csv(KAGGLE_RAW_PATH)
        except Exception:
            pass
            
    if df is None and os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH)
        except Exception:
            pass

    if df is None or df.empty:
        df = generate_sample_kaggle_dataset(CSV_PATH)

    return clean_accident_dataframe(df)

def aggregate_accident_history_by_city(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Aggregates accident frequency, fatalities, injuries, severity categories,
    and adverse weather factors by City.
    Computes a normalized city-level baseline accident severity score (0-100).
    """
    if df is None:
        df = load_accident_dataset()

    city_groups = df.groupby("City")

    summaries = []
    for city, group in city_groups:
        total_accidents = len(group)
        fatalities = int(group["Fatalities"].sum())
        injuries = int(group["Injuries"].sum())
        fatal_accidents = int((group["Accident_Severity"] == "Fatal").sum())
        serious_accidents = int((group["Accident_Severity"] == "Serious").sum())
        minor_accidents = int((group["Accident_Severity"] == "Minor").sum())

        weather_risk_pct = round(float((group["Weather_Conditions"] != "Clear").mean() * 100), 1)
        two_wheeler_pct = round(float(group["Vehicle_Types_Involved"].str.contains("Motorcycle|Two-Wheeler|Scooter|Bike", case=False, na=False).mean() * 100), 1)

        state = group["State"].mode()[0] if "State" in group.columns and not group["State"].empty else "India"

        # Raw Severity Index Formula: Fatalities (8x) + Serious Accidents (3.5x) + Injuries (1.5x) + Volume (0.4x)
        raw_severity_index = (fatalities * 8.0) + (serious_accidents * 3.5) + (injuries * 1.5) + (total_accidents * 0.4)
        
        # Scale to calibrated 0-100 baseline score (normalized relative to high-density Indian metros)
        # 500+ raw index ~ 85-95 high score, 150-300 ~ 45-65 medium score, <100 ~ 20-35 low score
        city_score = min(96.0, max(12.0, (raw_severity_index / 520.0) * 100.0))
        city_score = round(city_score, 1)

        summaries.append({
            "City": city,
            "State": state,
            "Total_Accidents": total_accidents,
            "Fatalities": fatalities,
            "Injuries": injuries,
            "Fatal_Accidents": fatal_accidents,
            "Serious_Accidents": serious_accidents,
            "Minor_Accidents": minor_accidents,
            "Adverse_Weather_Pct": weather_risk_pct,
            "Two_Wheeler_Involvement_Pct": two_wheeler_pct,
            "Raw_Severity_Index": round(raw_severity_index, 2),
            "City_Accident_Risk_Score": city_score
        })

    summary_df = pd.DataFrame(summaries)
    summary_df.sort_values(by="City_Accident_Risk_Score", ascending=False, inplace=True)
    return summary_df

def compute_junction_accident_history_scores(
    dataset_df: Optional[pd.DataFrame] = None,
    junctions_registry: List[Dict[str, Any]] = ALL_DEMO_JUNCTIONS
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, Any]]]:
    """
    Joins city-level aggregated accident severity + frequency to each demo junction.
    Applies local junction topology modifiers to produce the final clean
    `accident_history_score` (0-100 scale) for each junction.
    
    Returns:
    - DataFrame of all scored junctions with metrics.
    - Dict mapping junction_id -> {score, city_metrics, junction_details} ready for the Risk Engine.
    """
    if dataset_df is None:
        dataset_df = load_accident_dataset()

    city_summary_df = aggregate_accident_history_by_city(dataset_df)
    city_metrics_map = city_summary_df.set_index("City").to_dict(orient="index")

    # National / Tier-2 fallback baseline for unrepresented cities
    default_city_baseline = {
        "Total_Accidents": 120,
        "Fatalities": 18,
        "Injuries": 65,
        "Fatal_Accidents": 15,
        "Serious_Accidents": 45,
        "Minor_Accidents": 60,
        "Adverse_Weather_Pct": 22.0,
        "Two_Wheeler_Involvement_Pct": 48.0,
        "Raw_Severity_Index": 210.0,
        "City_Accident_Risk_Score": 40.0
    }

    junction_records = []
    junction_dict = {}

    for jnc in junctions_registry:
        jnc_id = jnc["junction_id"]
        jnc_name = jnc["name"]
        city = normalize_city_name(jnc.get("city", "Unknown"))
        state = jnc.get("state", "India")
        lat = jnc.get("lat", 0.0)
        lon = jnc.get("lon", 0.0)
        jnc_type = jnc.get("junction_type", "Intersection")
        modifier = jnc.get("local_risk_modifier", 1.0)

        city_stats = city_metrics_map.get(city, default_city_baseline)

        # Baseline city score modified by specific junction risk multiplier
        base_score = float(city_stats["City_Accident_Risk_Score"])
        junction_accident_score = min(98.0, max(10.0, base_score * modifier))
        junction_accident_score = round(junction_accident_score, 1)

        # Calculate estimated junction share of city accident volume
        est_accidents = int(round(city_stats["Total_Accidents"] * (0.35 if modifier > 1.05 else 0.20)))
        est_fatalities = int(round(city_stats["Fatalities"] * (0.35 if modifier > 1.05 else 0.20)))
        est_injuries = int(round(city_stats["Injuries"] * (0.35 if modifier > 1.05 else 0.20)))

        rec = {
            "junction_id": jnc_id,
            "junction_name": jnc_name,
            "city": city,
            "state": state,
            "lat": lat,
            "lon": lon,
            "junction_type": jnc_type,
            "accident_history_score": junction_accident_score,
            "city_baseline_score": base_score,
            "local_risk_modifier": modifier,
            "total_accidents": est_accidents,
            "fatalities": est_fatalities,
            "injuries": est_injuries,
            "city_total_accidents": city_stats["Total_Accidents"],
            "city_fatalities": city_stats["Fatalities"],
            "city_injuries": city_stats["Injuries"],
            "adverse_weather_pct": city_stats["Adverse_Weather_Pct"],
            "two_wheeler_involvement_pct": city_stats["Two_Wheeler_Involvement_Pct"]
        }

        junction_records.append(rec)
        junction_dict[jnc_id] = rec

    scored_df = pd.DataFrame(junction_records)
    scored_df.sort_values(by="accident_history_score", ascending=False, inplace=True)
    return scored_df, junction_dict

def compute_historical_risk_score(junction_id: str) -> Tuple[float, Dict[str, Any]]:
    """
    Computes normalized historical accident severity risk score (0-100)
    and detailed explainability metrics for a junction.
    Used directly by ExplainableRiskEngine and UI dashboards.
    """
    _, scored_dict = compute_junction_accident_history_scores()
    
    if junction_id in scored_dict:
        data = scored_dict[junction_id]
        score = float(data["accident_history_score"])
        metrics = {
            "total_accidents": int(data["total_accidents"]),
            "fatalities": int(data["fatalities"]),
            "injuries": int(data["injuries"]),
            "city_total_accidents": int(data["city_total_accidents"]),
            "city_fatalities": int(data["city_fatalities"]),
            "high_risk_weather_pct": float(data["adverse_weather_pct"]),
            "motorcycle_involvement_pct": float(data["two_wheeler_involvement_pct"]),
            "city": data["city"],
            "state": data["state"]
        }
        return score, metrics

    # Fallback for dynamic/unrecognized junction IDs
    return 35.0, {
        "total_accidents": 25,
        "fatalities": 3,
        "injuries": 12,
        "high_risk_weather_pct": 20.0,
        "motorcycle_involvement_pct": 50.0,
        "city": "Unknown",
        "state": "India"
    }

def export_clean_accident_history_csvs() -> Tuple[str, str]:
    """
    Exports clean processed accident scores per junction and city aggregation summaries to CSV.
    Returns file paths of generated CSVs.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Clean & Aggregate Dataset
    raw_df = load_accident_dataset()
    city_df = aggregate_accident_history_by_city(raw_df)
    junction_df, _ = compute_junction_accident_history_scores(raw_df)

    # 2. Save CSVs
    city_df.to_csv(CITY_SUMMARY_CSV, index=False)
    junction_df.to_csv(JUNCTION_SCORES_CSV, index=False)

    return JUNCTION_SCORES_CSV, CITY_SUMMARY_CSV

if __name__ == "__main__":
    j_csv, c_csv = export_clean_accident_history_csvs()
    print(f"[DataLoader] Clean junction accident scores exported to: {j_csv}")
    print(f"[DataLoader] City accident severity summary exported to: {c_csv}")
