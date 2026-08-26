import math
import requests
from typing import List, Dict, Any, Tuple, Optional

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points on the Earth in kilometers.
    """
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def find_nearest_junction(
    lat: float,
    lon: float,
    junctions: List[Any],
    threshold_km: float = 1.0
) -> Tuple[Optional[Any], float]:
    """
    Finds the nearest junction to the given (lat, lon) coordinates.
    Returns (nearest_junction_obj_or_dict, distance_km).
    If minimum distance exceeds threshold_km, junction returned is None.
    """
    nearest = None
    min_dist = float("inf")

    for j in junctions:
        # Extract lat/lon whether j is a dict or object
        if isinstance(j, dict):
            j_lat = j.get("lat")
            j_lon = j.get("lon")
        else:
            j_lat = getattr(j, "lat", None)
            j_lon = getattr(j, "lon", None)

        if j_lat is not None and j_lon is not None:
            try:
                dist = haversine_distance(lat, lon, float(j_lat), float(j_lon))
                if dist < min_dist:
                    min_dist = dist
                    nearest = j
            except (ValueError, TypeError):
                continue

    if nearest and min_dist <= threshold_km:
        return nearest, min_dist
    return None, min_dist if min_dist != float("inf") else 0.0

def reverse_geocode_location(lat: float, lon: float) -> str:
    """
    Reverse-geocodes any (lat, lon) point on the map to detect street/area/intersection name.
    Falls back to formatted lat/lon string if reverse geocoding is unreachable.
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18"
        headers = {"User-Agent": "JunctionGuardAI/1.0"}
        resp = requests.get(url, headers=headers, timeout=2.5)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get("address", {})
            road = address.get("road") or address.get("pedestrian") or address.get("suburb") or address.get("neighbourhood") or address.get("amenity")
            suburb = address.get("suburb") or address.get("city_district") or address.get("city") or "Location"
            if road and suburb:
                return f"{road}, {suburb}"
            elif road:
                return str(road)
            display_name = data.get("display_name", "")
            if display_name:
                parts = [p.strip() for p in display_name.split(",")]
                return ", ".join(parts[:2])
    except Exception as e:
        print(f"[Reverse Geocode Note] {e}")
    return f"Location ({lat:.4f}, {lon:.4f})"
