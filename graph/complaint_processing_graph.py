import logging
from typing import Optional
from typing_extensions import TypedDict

from langgraph.graph import END, StateGraph

from models.db import departments_collection
from services.ai_services import AIServiceError, analyze_image_for_civic_issue, map_issue_to_department
from services.duplicate_service import find_duplicate_complaint
from services.location_service import find_ward_by_coordinates
from services.officer_service import find_assignable_officer


logger = logging.getLogger(__name__)


class State(TypedDict):
    complaint_id: str
    user_id: str
    description: str
    image_url: str
    lat: float
    lon: float
    issue_type: Optional[str]
    has_issue: Optional[bool]
    issue_confidence: Optional[float]
    rejection_reason: Optional[str]
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


def validation_node(state: State) -> State:
    logger.info("Graph step=validation complaint_id=%s", state.get("complaint_id"))
    if not state.get("description"):
        raise ValueError("description is required")
    if not state.get("image_url"):
        raise ValueError("image is required")

    lat = state.get("lat")
    lon = state.get("lon")
    if lat is None or lon is None:
        raise ValueError("latitude and longitude are required")
    if not (-90 <= lat <= 90):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180 <= lon <= 180):
        raise ValueError("longitude must be between -180 and 180")

    state["status"] = "PENDING"
    return state


def vision_node(state: State) -> State:
    logger.info("Graph step=vision complaint_id=%s", state.get("complaint_id"))
    try:
        analysis = analyze_image_for_civic_issue(
            state["image_url"],
            state.get("description", ""),
        )
    except AIServiceError as exc:
        state["has_issue"] = False
        state["issue_type"] = None
        state["issue_confidence"] = 0.0
        state["rejection_reason"] = str(exc)
        state["status"] = "REJECTED"
        logger.info("Graph step=vision rejected error=%s", exc)
        return state

    state["issue_confidence"] = analysis.confidence_score
    state["rejection_reason"] = analysis.reason

    if analysis.has_issue and analysis.issue_type:
        state["has_issue"] = True
        state["issue_type"] = analysis.issue_type
        state["status"] = "PENDING"
        logger.info(
            "Graph step=vision accepted issue_type=%s confidence=%s",
            analysis.issue_type,
            analysis.confidence_score,
        )
    else:
        state["has_issue"] = False
        state["issue_type"] = None
        state["status"] = "REJECTED"
        logger.info(
            "Graph step=vision rejected confidence=%s reason=%s",
            analysis.confidence_score,
            analysis.reason,
        )

    return state


def vision_router(state: State) -> str:
    if state.get("has_issue"):
        return "continue"
    return "no_issue"


def department_mapping_node(state: State) -> State:
    logger.info("Graph step=department_mapping complaint_id=%s", state.get("complaint_id"))
    issue_type = state.get("issue_type")
    if not issue_type:
        raise ValueError("issue type missing for department mapping")

    department_name = map_issue_to_department(issue_type)
    department_doc = departments_collection.find_one({"name": department_name})
    if not department_doc:
        raise ValueError(f"Department not found in DB: {department_name}")

    state["department_id"] = str(department_doc["_id"])
    logger.info("Graph step=department_mapping department_id=%s", state.get("department_id"))
    return state


def location_node(state: State) -> State:
    logger.info("Graph step=location complaint_id=%s", state.get("complaint_id"))
    ward_doc = find_ward_by_coordinates(state["lat"], state["lon"])
    if not ward_doc:
        raise ValueError("No ward found for provided latitude/longitude")

    state["ward_id"] = str(ward_doc["_id"])
    logger.info("Graph step=location ward_id=%s", state.get("ward_id"))
    return state


def duplicate_check_node(state: State) -> State:
    logger.info("Graph step=duplicate_check complaint_id=%s", state.get("complaint_id"))
    duplicate = find_duplicate_complaint(
        issue_type=state["issue_type"] or "",
        lat=state["lat"],
        lon=state["lon"],
        radius_km=0.5,
    )

    if duplicate:
        state["is_duplicate"] = True
        state["parent_complaint_id"] = str(duplicate.get("complaint_id") or duplicate.get("_id"))
        state["status"] = "DUPLICATE"
    else:
        state["is_duplicate"] = False

    logger.info(
        "Graph step=duplicate_check is_duplicate=%s parent_complaint_id=%s",
        state.get("is_duplicate"),
        state.get("parent_complaint_id"),
    )
    return state


def duplicate_router(state: State) -> str:
    if state.get("is_duplicate"):
        return "duplicate"
    return "continue"


def assign_officer_node(state: State) -> State:
    logger.info("Graph step=assign_officer complaint_id=%s", state.get("complaint_id"))
    if not state.get("department_id") or not state.get("ward_id"):
        raise ValueError("department_id and ward_id are required for officer assignment")

    officer = find_assignable_officer(state["department_id"], state["ward_id"])
    if officer:
        state["officer_id"] = str(officer["_id"])
    else:
        state["officer_id"] = None
    logger.info("Graph step=assign_officer officer_id=%s", state.get("officer_id"))
    return state


builder = StateGraph(State)

builder.add_node("validation", validation_node)
builder.add_node("vision", vision_node)
builder.add_node("department_mapping", department_mapping_node)
builder.add_node("location", location_node)
builder.add_node("duplicate_check", duplicate_check_node)
builder.add_node("assign_officer", assign_officer_node)

builder.set_entry_point("validation")
builder.add_edge("validation", "vision")
builder.add_conditional_edges(
    "vision",
    vision_router,
    {
        "continue": "department_mapping",
        "no_issue": END,
    },
)
builder.add_edge("department_mapping", "location")
builder.add_edge("location", "duplicate_check")

builder.add_conditional_edges(
    "duplicate_check",
    duplicate_router,
    {
        "duplicate": END,
        "continue": "assign_officer",
    },
)

builder.add_edge("assign_officer", END)

complaint_processing_graph = builder.compile()
