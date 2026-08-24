import os
import sys
from typing import List, Optional

# Ensure that the root directory is on the python path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.schema import JunctionRecord

def load_junctions() -> List[JunctionRecord]:
    """
    Loads junctions from database/data source.
    
    TODO: The backend will replace this placeholder implementation with real database 
    queries and risk engine scoring. Currently returns placeholder junctions in Kolhapur 
    with risk metrics set to None (awaiting data).
    """
    placeholders = [
        JunctionRecord(
            junction_id="J001",
            name="Shivaji Chowk",
            lat=16.6996,
            lon=74.2433,
            risk_score=None,
            risk_level=None,
            contributing_factors=None,
            last_updated=None
        ),
        JunctionRecord(
            junction_id="J002",
            name="Rajaram Corner",
            lat=16.7025,
            lon=74.2505,
            risk_score=None,
            risk_level=None,
            contributing_factors=None,
            last_updated=None
        ),
        JunctionRecord(
            junction_id="J003",
            name="Dabholkar Corner",
            lat=16.7001,
            lon=74.2482,
            risk_score=None,
            risk_level=None,
            contributing_factors=None,
            last_updated=None
        ),
        JunctionRecord(
            junction_id="J004",
            name="Cyber Chowk",
            lat=16.6853,
            lon=74.2541,
            risk_score=None,
            risk_level=None,
            contributing_factors=None,
            last_updated=None
        ),
        JunctionRecord(
            junction_id="J005",
            name="Kawala Naka",
            lat=16.7018,
            lon=74.2575,
            risk_score=None,
            risk_level=None,
            contributing_factors=None,
            last_updated=None
        )
    ]
    return placeholders
