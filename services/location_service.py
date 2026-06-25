from typing import Any, Dict, Optional

from shapely.geometry import Point, Polygon

from models.db import wards_collection


class LocationServiceError(Exception):
    pass


def find_ward_by_coordinates(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    point = Point(lon, lat)
    wards = wards_collection.find({"boundary": {"$exists": True}})

    for ward in wards:
        boundary = ward.get("boundary")
        if not boundary or len(boundary) < 4:
            continue

        polygon = Polygon(boundary)
        if not polygon.is_valid:
            continue

        if polygon.contains(point) or polygon.touches(point):
            return ward

    return None
