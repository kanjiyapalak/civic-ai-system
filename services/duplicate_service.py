import math
from typing import Any, Dict, Optional

from models.db import complaints_collection

# Only open complaints can be duplicates — completed/rejected cases allow a fresh report.
_ACTIVE_DUPLICATE_STATUSES = ("PENDING", "IN_PROGRESS")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def find_duplicate_complaint(
    issue_type: str,
    lat: float,
    lon: float,
    radius_km: float = 0.5,
) -> Optional[Dict[str, Any]]:
    cursor = complaints_collection.find(
        {
            "issue_type": issue_type,
            "is_duplicate": {"$ne": True},
            "status": {"$in": list(_ACTIVE_DUPLICATE_STATUSES)},
        }
    )

    for complaint in cursor:
        location = complaint.get("location", {})
        c_lat = location.get("lat")
        c_lon = location.get("lon")
        if c_lat is None or c_lon is None:
            continue

        distance = _haversine_km(lat, lon, c_lat, c_lon)
        if distance <= radius_km:
            return complaint

    return None
