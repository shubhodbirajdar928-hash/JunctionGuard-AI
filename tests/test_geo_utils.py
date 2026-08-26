import pytest
from src.geo_utils import haversine_distance, find_nearest_junction

def test_haversine_distance():
    # Distance between Silk Board (12.9177, 77.6238) and Dairy Circle (12.9348, 77.6047) ~3.0 km
    dist = haversine_distance(12.9177, 77.6238, 12.9348, 77.6047)
    assert 2.5 <= dist <= 3.5

def test_find_nearest_junction_within_threshold():
    sample_junctions = [
        {"junction_id": "J001", "name": "Silk Board Junction", "lat": 12.9177, "lon": 77.6238},
        {"junction_id": "J002", "name": "Dairy Circle Junction", "lat": 12.9348, "lon": 77.6047},
        {"junction_id": "J003", "name": "Hebbal Flyover Junction", "lat": 13.0358, "lon": 77.5970}
    ]

    # Coordinate 200 meters away from Silk Board
    click_lat = 12.9185
    click_lon = 77.6242

    nearest, dist_km = find_nearest_junction(click_lat, click_lon, sample_junctions, threshold_km=1.0)
    assert nearest is not None
    assert nearest["junction_id"] == "J001"
    assert dist_km < 0.3

def test_find_nearest_junction_exceeds_threshold():
    sample_junctions = [
        {"junction_id": "J001", "name": "Silk Board Junction", "lat": 12.9177, "lon": 77.6238}
    ]

    # Coordinate far away in Whitefield (~15km away)
    click_lat = 12.9698
    click_lon = 77.7499

    nearest, dist_km = find_nearest_junction(click_lat, click_lon, sample_junctions, threshold_km=1.0)
    assert nearest is None
    assert dist_km > 10.0
