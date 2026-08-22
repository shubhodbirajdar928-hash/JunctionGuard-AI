"""
Data Contract schema for JunctionGuard AI.
Every module (Vision, Analytics, DB, Frontend) must adhere strictly to this schema.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ContributingFactor(BaseModel):
    factor: str
    weight: float = Field(..., ge=0.0, le=1.0, description="Normalized weight or impact score between 0 and 1")

class JunctionRecord(BaseModel):
    junction_id: str
    name: str
    lat: float
    lon: float
    risk_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Junction Risk Score 0-100")
    risk_level: Optional[str] = Field(None, description="LOW, MEDIUM, or HIGH")
    contributing_factors: Optional[List[Dict[str, Any]]] = Field(
        None, description="List of factor dicts e.g. [{'factor': 'Accident Severity', 'weight': 0.4}]"
    )
    last_updated: Optional[str] = Field(None, description="Timestamp string ISO or YYYY-MM-DD HH:MM:SS")

    @classmethod
    def calculate_risk_level(cls, score: Optional[float]) -> Optional[str]:
        if score is None:
            return None
        if score >= 70.0:
            return "HIGH"
        elif score >= 40.0:
            return "MEDIUM"
        else:
            return "LOW"

    def to_dict(self) -> Dict[str, Any]:
        """Ensures strict adherence to data contract dict format."""
        return {
            "junction_id": self.junction_id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "risk_score": round(self.risk_score, 1) if self.risk_score is not None else None,
            "risk_level": self.risk_level or self.calculate_risk_level(self.risk_score),
            "contributing_factors": self.contributing_factors,
            "last_updated": self.last_updated or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
