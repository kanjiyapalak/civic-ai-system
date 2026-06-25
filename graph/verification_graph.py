import io
import math
import os
from typing import Optional

from PIL import ExifTags, Image
from services.image_loader import load_image_bytes, load_image_bytes_and_mime
from typing_extensions import TypedDict

from google import genai
from google.genai import types
from langgraph.graph import END, StateGraph


class State(TypedDict):
    complaint_id: str
    user_id: str
    description: str
    image_url: str
    lat: float
    lon: float
    issue_type: Optional[str]
    department_id: Optional[str]
    ward_id: Optional[str]
    officer_id: Optional[str]
    is_duplicate: bool
    parent_complaint_id: Optional[str]
    status: str
    is_resolved: bool
    before_image_url: Optional[str]
    after_image_url: Optional[str]
    location_match: Optional[bool]
    issue_solved: Optional[bool]


def upload_node(state: State) -> State:
    required_fields = ("before_image_url", "after_image_url", "lat", "lon")
    missing_fields = [field for field in required_fields if state.get(field) in (None, "")]
    if missing_fields:
        raise ValueError(f"Missing required verification fields: {', '.join(missing_fields)}")

    # Ensure coordinates are valid numeric values before downstream checks.
    try:
        float(state["lat"])
        float(state["lon"])
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("Invalid coordinates: lat and lon must be numeric") from exc

    return state


def location_check_node(state: State) -> State:
    def _load_image_bytes(image_ref: str) -> bytes:
        return load_image_bytes(image_ref)

    def _dms_to_decimal(values, ref: str) -> Optional[float]:
        if not values:
            return None

        def _to_float(value) -> float:
            if hasattr(value, "numerator") and hasattr(value, "denominator"):
                denominator = value.denominator or 1
                return float(value.numerator) / float(denominator)

            if isinstance(value, tuple) and len(value) == 2:
                denominator = value[1] or 1
                return float(value[0]) / float(denominator)

            return float(value)

        degrees = _to_float(values[0])
        minutes = _to_float(values[1])
        seconds = _to_float(values[2])

        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ("S", "W"):
            decimal *= -1.0
        return decimal

    def _extract_gps(image_bytes: bytes) -> Optional[tuple[float, float]]:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            exif = image.getexif()
        except Exception:
            return None

        if not exif:
            return None

        gps_tag = next((tag for tag, name in ExifTags.TAGS.items() if name == "GPSInfo"), None)
        if not gps_tag:
            return None

        gps_info = exif.get(gps_tag)
        if not gps_info:
            return None

        gps_data = {ExifTags.GPSTAGS.get(key, key): value for key, value in gps_info.items()}
        lat_values = gps_data.get("GPSLatitude")
        lat_ref = gps_data.get("GPSLatitudeRef")
        lon_values = gps_data.get("GPSLongitude")
        lon_ref = gps_data.get("GPSLongitudeRef")

        if not (lat_values and lat_ref and lon_values and lon_ref):
            return None

        lat = _dms_to_decimal(lat_values, str(lat_ref))
        lon = _dms_to_decimal(lon_values, str(lon_ref))
        if lat is None or lon is None:
            return None
        return (lat, lon)

    before_image_url = state["before_image_url"]
    after_image_url = state["after_image_url"]
    if not before_image_url or not after_image_url:
        raise ValueError("Both before_image_url and after_image_url are required")

    before_bytes = _load_image_bytes(before_image_url)
    after_bytes = _load_image_bytes(after_image_url)

    before_coords = _extract_gps(before_bytes) or (float(state["lat"]), float(state["lon"]))
    after_coords = _extract_gps(after_bytes) or (float(state["lat"]), float(state["lon"]))

    # Small geospatial threshold in degrees (~11m at equator) to tolerate GPS noise.
    threshold = 0.0001
    distance = math.hypot(before_coords[0] - after_coords[0], before_coords[1] - after_coords[1])
    location_match = distance <= threshold
    return {"location_match": location_match}


def gemini_check_node(state: State) -> State:
    before_image_url = state.get("before_image_url")
    after_image_url = state.get("after_image_url")
    if not before_image_url or not after_image_url:
        raise ValueError("Both before_image_url and after_image_url are required")

    def _load_image_bytes_and_mime(image_ref: str) -> tuple[bytes, str]:
        return load_image_bytes_and_mime(image_ref)

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return {"issue_solved": False}

    try:
        before_bytes, before_mime = _load_image_bytes_and_mime(before_image_url)
        after_bytes, after_mime = _load_image_bytes_and_mime(after_image_url)

        prompt = (
            "Compare these two images. The first image shows a civic issue. "
            "The second image shows the same location after work was done. "
            "Is the issue resolved? Answer only YES or NO."
        )

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        client = genai.Client(api_key=gemini_api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=[
                prompt,
                types.Part.from_bytes(data=before_bytes, mime_type=before_mime),
                types.Part.from_bytes(data=after_bytes, mime_type=after_mime),
            ],
        )

        normalized = (getattr(response, "text", "") or "").strip().upper()
        issue_solved = normalized == "YES"
        if normalized not in {"YES", "NO"}:
            issue_solved = False
    except Exception:
        issue_solved = False

    return {"issue_solved": issue_solved}


def decision_node(state: State) -> State:
    return state


def verification_router(state: State) -> str:
    if state["location_match"] is True and state["issue_solved"] is True:
        return "end_complete"
    return "end_in_progress"


builder = StateGraph(State)

builder.add_node("upload_node", upload_node)
builder.add_node("location_check_node", location_check_node)
builder.add_node("gemini_check_node", gemini_check_node)
builder.add_node("decision_node", decision_node)

builder.set_entry_point("upload_node")

builder.add_edge("upload_node", "location_check_node")
builder.add_edge("upload_node", "gemini_check_node")
builder.add_edge("location_check_node", "decision_node")
builder.add_edge("gemini_check_node", "decision_node")

builder.add_conditional_edges(
    "decision_node",
    verification_router,
    {
        "end_complete": END,
        "end_in_progress": END,
    },
)

verification_graph = builder.compile()
