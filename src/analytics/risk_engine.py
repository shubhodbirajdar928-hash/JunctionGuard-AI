"""
Explainable Junction Risk Engine for JunctionGuard AI.
Combines historical accidents, live vision analytics, citizen reports, and weather factors.
Generates an overall 0-100 Junction Risk Score and contributing factor breakdown.
"""

from typing import Dict, Any, List, Tuple
from src.analytics.data_loader import compute_historical_risk_score
from src.database import fetch_citizen_reports, update_junction_risk

class ExplainableRiskEngine:
    """
    Computes a composite 0-100 Junction Risk Score with transparent factor weights.
    Weights:
    - Historical Accident Severity Index: 35%
    - Real-time Traffic & Vision Metrics: 35%
    - Citizen Hazard Reports & Near-Misses: 20%
    - Environmental & Weather Factor: 10%
    """

    def __init__(self):
        self.w_historical = 0.35
        self.w_vision = 0.35
        self.w_citizen = 0.20
        self.w_env = 0.10

    def compute_junction_risk(
        self,
        junction_id: str,
        vision_risk_score: float = 65.0,
        weather_condition: str = "Clear",
        is_night: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates total risk score and produces explainable contributing factors.
        Returns dict matching JunctionRecord fields.
        """
        # 1. Historical Risk (0-100)
        hist_score, hist_metrics = compute_historical_risk_score(junction_id)

        # 2. Vision Risk (0-100)
        vis_score = max(0.0, min(100.0, vision_risk_score))

        # 3. Citizen Reports Risk (0-100)
        reports = fetch_citizen_reports(junction_id)
        if reports:
            num_reports = len(reports)
            avg_severity = sum(r.get("severity", 3) for r in reports) / num_reports
            cit_score = min(100.0, (num_reports * 12.0) + (avg_severity * 10.0))
        else:
            # Baseline default for demo junctions
            cit_score = 45.0

        # 4. Environmental Risk (0-100)
        env_score = 15.0
        if weather_condition in ["Heavy Rain", "Monsoon Pour"]:
            env_score += 45.0
        elif weather_condition in ["Fog / Mist"]:
            env_score += 35.0
        if is_night:
            env_score += 25.0
        env_score = min(100.0, env_score)

        # Composite Score Calculation
        total_risk = (
            (hist_score * self.w_historical) +
            (vis_score * self.w_vision) +
            (cit_score * self.w_citizen) +
            (env_score * self.w_env)
        )
        total_risk = round(max(0.0, min(100.0, total_risk)), 1)

        # Explainability Factor Breakdown
        # Calculate raw contribution values
        c_hist = hist_score * self.w_historical
        c_vis = vis_score * self.w_vision
        c_cit = cit_score * self.w_citizen
        c_env = env_score * self.w_env
        denom = max(1.0, c_hist + c_vis + c_cit + c_env)

        contributing_factors = [
            {
                "factor": f"Historical Severity ({hist_metrics.get('fatalities', 0)} Fatalities)",
                "weight": round(c_hist / denom, 2)
            },
            {
                "factor": "Real-time Traffic Density & Conflict Index",
                "weight": round(c_vis / denom, 2)
            },
            {
                "factor": f"Citizen Hazard Reports ({len(reports)} Active)",
                "weight": round(c_cit / denom, 2)
            },
            {
                "factor": f"Environmental Risk ({weather_condition})",
                "weight": round(c_env / denom, 2)
            }
        ]

        # Sort factors by highest contribution weight
        contributing_factors.sort(key=lambda x: x["weight"], reverse=True)

        # Update in SQLite DB
        update_junction_risk(junction_id, total_risk, contributing_factors)

        return {
            "junction_id": junction_id,
            "risk_score": total_risk,
            "contributing_factors": contributing_factors,
            "hist_metrics": hist_metrics
        }
