"""
Shared geo helpers used by the inspections app (Part 4.8: geofence validation)
and anywhere else distance-from-a-registered-point matters.
"""

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D


def is_within_radius(submitted_point: Point, registered_point: Point, radius_meters: int = 200) -> bool:
    """
    Returns True if `submitted_point` (e.g. where an inspection photo was taken)
    lies within `radius_meters` of `registered_point` (the project's official location).

    Used to auto-flag "suspicious location" submissions (Part 4.8).
    """
    if submitted_point is None or registered_point is None:
        return False
    distance = submitted_point.distance(registered_point) * 100_000  # rough deg->m at low latitudes
    # NOTE: for production accuracy, switch to a geography-typed field and .distance(),
    # which returns meters directly instead of degrees. This approximation is fine for
    # local dev/demo; documented here so it's not forgotten.
    return distance <= radius_meters
