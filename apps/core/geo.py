"""
Shared geo helpers used by the inspections app (Part 4.8: geofence validation).

LOCAL DEV MODE: plain latitude/longitude floats + the Haversine formula,
since we're not on PostGIS yet. Once we switch to Postgres+PostGIS, this
can be replaced with a one-line `.distance()` call on GeoDjango PointFields
— the function signature below is written so callers won't need to change.
"""

from math import atan2, cos, radians, sin, sqrt

EARTH_RADIUS_METERS = 6_371_000


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in meters."""
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)

    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return EARTH_RADIUS_METERS * c


def is_within_radius(
    submitted_lat: float, submitted_lon: float,
    registered_lat: float, registered_lon: float,
    radius_meters: int = 200,
) -> bool:
    """
    Returns True if a submitted GPS point (e.g. where an inspection photo
    was taken) lies within `radius_meters` of an institute's registered
    location. Used to auto-flag "suspicious location" submissions (Part 4.8).
    """
    if None in (submitted_lat, submitted_lon, registered_lat, registered_lon):
        return False
    return distance_meters(submitted_lat, submitted_lon, registered_lat, registered_lon) <= radius_meters
