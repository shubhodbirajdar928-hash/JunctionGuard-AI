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

def get_ip_location() -> tuple[float, float, str] | None:
    """
    Gets approximate user location via IP geolocation (no GPS / browser permission needed).
    Tries ipinfo.io first, then ip-api.com as fallback.
    Returns (lat, lon, city_label) or None if both services fail.
    """
    # --- ipinfo.io (primary) ---
    try:
        resp = requests.get("https://ipinfo.io/json", timeout=3.0,
                            headers={"Accept": "application/json"})
        if resp.status_code == 200:
            data = resp.json()
            loc = data.get("loc", "")          # "12.9716,77.5946"
            city = data.get("city", "")
            region = data.get("region", "")
            if loc and "," in loc:
                lat, lon = (float(x) for x in loc.split(","))
                label = f"{city}, {region}" if city and region else city or region or "Your Location"
                return lat, lon, label
    except Exception:
        pass

    # --- ip-api.com (fallback, free tier) ---
    try:
        resp = requests.get("http://ip-api.com/json?fields=status,lat,lon,city,regionName",
                            timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                lat = float(data["lat"])
                lon = float(data["lon"])
                city = data.get("city", "")
                region = data.get("regionName", "")
                label = f"{city}, {region}" if city and region else city or region or "Your Location"
                return lat, lon, label
    except Exception:
        pass

    return None

def forward_geocode_location(query: str) -> Optional[Tuple[float, float, str]]:
    """
    Geocodes a search string (city, area, road, landmark) to (lat, lon, display_name).
    """
    if not query or not query.strip():
        return None
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query.strip())}&format=json&limit=1&addressdetails=1"
        headers = {"User-Agent": "JunctionGuardAI/1.0"}
        resp = requests.get(url, headers=headers, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                item = data[0]
                lat = float(item["lat"])
                lon = float(item["lon"])
                display_name = item.get("display_name", query)
                parts = [p.strip() for p in display_name.split(",")]
                short_name = ", ".join(parts[:2]) if len(parts) >= 2 else display_name
                return lat, lon, short_name
    except Exception as e:
        print(f"[Forward Geocode Note] {e}")
    return None

def reverse_geocode_location(lat: float, lon: float) -> str:
    """
    Reverse-geocodes any (lat, lon) point on the map to detect street/area/intersection name.
    Tries road -> suburb -> village -> town -> city level progressively.
    Falls back to formatted lat/lon string if reverse geocoding is unreachable.
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18"
        headers = {"User-Agent": "JunctionGuardAI/1.0"}
        resp = requests.get(url, headers=headers, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get("address", {})

            road     = (address.get("road")
                        or address.get("pedestrian")
                        or address.get("footway")
                        or address.get("path")
                        or address.get("amenity")
                        or address.get("tourism")
                        or address.get("landuse"))
            locality = (address.get("neighbourhood")
                        or address.get("suburb")
                        or address.get("village")
                        or address.get("hamlet")
                        or address.get("city_district")
                        or address.get("town")
                        or address.get("city")
                        or address.get("county"))
            state    = address.get("state", "")

            if road and locality:
                return f"{road}, {locality}"
            if road and state:
                return f"{road}, {state}"
            if locality and state:
                return f"{locality}, {state}"
            if road:
                return str(road)
            if locality:
                return str(locality)

            display_name = data.get("display_name", "")
            if display_name:
                parts = [p.strip() for p in display_name.split(",")]
                return ", ".join(parts[:2])
    except Exception as e:
        print(f"[Reverse Geocode Note] {e}")
    return f"Location ({lat:.4f}, {lon:.4f})"
