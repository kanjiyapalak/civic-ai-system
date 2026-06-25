import logging
from datetime import datetime
from typing import Any, Dict, Generator, Optional
import uuid
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from graph.verification_graph import verification_graph
from graph.complaint_processing_graph import complaint_processing_graph
from models.db import (
    complaints_collection,
    departments_collection,
    images_collection,
    officers_collection,
    users_collection,
    wards_collection,
)
from services.auth_service import require_role
from services.notification_service import create_assignment_notification_and_send, mark_notification_accepted
from services.officer_service import find_officer_by_user_id, get_officer_user
from services.storage_service import resolve_public_url, upload_complaint_image
from services.stream_service import (
    PROCESSING_STEP_MESSAGES,
    VERIFICATION_STEP_MESSAGES,
    format_sse,
)

router = APIRouter(tags=["complaints"])
logger = logging.getLogger(__name__)


def _get_name_by_id(collection, object_id_str: Optional[str], field_name: str = "name") -> Optional[str]:
    if not object_id_str:
        return None

    try:
        object_id = ObjectId(object_id_str)
    except Exception:
        return None

    doc = collection.find_one({"_id": object_id})
    if not doc:
        return None
    return doc.get(field_name)


def _find_complaint_by_reference(reference: Optional[str]):
    if not reference:
        return None

    complaint = complaints_collection.find_one({"complaint_id": reference})
    if complaint:
        return complaint

    try:
        return complaints_collection.find_one({"_id": ObjectId(reference)})
    except Exception:
        return None


def _get_before_image_ref(complaint_id: str) -> Optional[str]:
    before_image = images_collection.find_one(
        {"complaint_id": complaint_id, "type": "BEFORE"},
        sort=[("created_at", 1)],
    )
    if before_image:
        return before_image.get("image_url")
    return None


def _find_before_image_url(complaint_id: str) -> Optional[str]:
    return resolve_public_url(_get_before_image_ref(complaint_id))


def _resolve_user_name(user_id: Any) -> Optional[str]:
    if not user_id:
        return None

    try:
        oid = ObjectId(user_id)
    except Exception:
        oid = None

    if oid:
        user = users_collection.find_one({"_id": oid})
        if user:
            return user.get("name")

    user = users_collection.find_one({"_id": user_id})
    if user:
        return user.get("name")
    return None


def _resolve_officer_name(officer_id: Optional[str]) -> Optional[str]:
    if not officer_id:
        return None

    officer_doc = None
    try:
        officer_doc = officers_collection.find_one({"_id": ObjectId(officer_id)})
    except Exception:
        officer_doc = officers_collection.find_one({"_id": officer_id})

    if not officer_doc:
        return None

    officer_user = get_officer_user(officer_doc)
    if officer_user:
        return officer_user.get("name")
    return None


def _user_id_query(user_id: str) -> Dict[str, Any]:
    try:
        oid = ObjectId(user_id)
    except Exception:
        oid = None

    if oid:
        return {"user_id": {"$in": [user_id, oid]}}
    return {"user_id": user_id}


def _normalize_complaint_id(complaint: Dict[str, Any]) -> Optional[str]:
    if not complaint:
        return None
    return str(complaint.get("complaint_id") or complaint.get("_id"))


def _enrich_processing_step(node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    extra: Dict[str, Any] = {}
    if node_name == "vision":
        if state.get("has_issue"):
            extra["issue_type"] = state.get("issue_type")
            extra["issue_confidence"] = state.get("issue_confidence")
            extra["message"] = (
                f"Issue verified in photo: {state.get('issue_type')} "
                f"(confidence {state.get('issue_confidence', 0):.0f}%)"
            )
        else:
            extra["has_issue"] = False
            extra["issue_confidence"] = state.get("issue_confidence")
            extra["rejection_reason"] = state.get("rejection_reason")
            extra["message"] = state.get("rejection_reason") or "No civic issue detected in the photo"
            extra["status"] = "rejected"
    elif node_name == "department_mapping" and state.get("department_id"):
        department = _get_name_by_id(departments_collection, state["department_id"])
        extra["department"] = department
        extra["message"] = f"Department selected: {department or 'Unknown'}"
    elif node_name == "location" and state.get("ward_id"):
        ward = _get_name_by_id(wards_collection, state["ward_id"])
        extra["ward"] = ward
        extra["message"] = f"Ward selected: {ward or 'Unknown'}"
    elif node_name == "duplicate_check":
        if state.get("is_duplicate"):
            extra["is_duplicate"] = True
            extra["message"] = "Duplicate complaint found — linking to existing case"
        else:
            extra["message"] = "No duplicate found — proceeding with assignment"
    elif node_name == "assign_officer":
        officer_name = _resolve_officer_name(state.get("officer_id"))
        extra["officer"] = officer_name
        if officer_name:
            extra["message"] = f"Officer assigned: {officer_name}"
        else:
            extra["message"] = "No officer available for this ward and department"
    return extra


def _enrich_verification_step(node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    extra: Dict[str, Any] = {}
    if node_name == "location_check_node":
        location_match = state.get("location_match")
        extra["location_match"] = location_match
        extra["message"] = (
            "Location verified — photos taken at the same site"
            if location_match
            else "Location mismatch — photos may be from different sites"
        )
    elif node_name == "gemini_check_node":
        issue_solved = state.get("issue_solved")
        extra["issue_solved"] = issue_solved
        extra["message"] = (
            "AI confirms the issue appears resolved"
            if issue_solved
            else "AI indicates the issue is not yet resolved"
        )
    elif node_name == "decision_node":
        if state.get("location_match") and state.get("issue_solved"):
            extra["message"] = "Verification passed — complaint will be marked completed"
        else:
            extra["message"] = "Verification failed — complaint stays in progress"
    return extra


def _build_initial_state(
    complaint_tracking_id: str,
    user_id: str,
    description: str,
    image_path: str,
    latitude: float,
    longitude: float,
) -> Dict[str, Any]:
    return {
        "complaint_id": complaint_tracking_id,
        "user_id": user_id,
        "description": description,
        "image_url": image_path,
        "lat": latitude,
        "lon": longitude,
        "issue_type": None,
        "has_issue": None,
        "issue_confidence": None,
        "rejection_reason": None,
        "department_id": None,
        "ward_id": None,
        "officer_id": None,
        "is_duplicate": False,
        "parent_complaint_id": None,
        "status": "PENDING",
        "is_resolved": False,
        "before_image_url": image_path,
        "after_image_url": None,
        "location_match": None,
        "issue_solved": None,
    }


def _persist_complaint(final_state: Dict[str, Any], now: datetime) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    parent_complaint = None
    parent_complaint_id = None
    is_duplicate = bool(final_state.get("is_duplicate"))
    if is_duplicate:
        parent_complaint = _find_complaint_by_reference(final_state.get("parent_complaint_id"))
        if not parent_complaint:
            raise HTTPException(status_code=500, detail="Duplicate complaint target not found")
        parent_complaint_id = _normalize_complaint_id(parent_complaint)

    if parent_complaint:
        complaint_doc = {
            "complaint_id": final_state["complaint_id"],
            "user_id": final_state["user_id"],
            "description": final_state["description"],
            "issue_type": final_state["issue_type"],
            "department_id": parent_complaint.get("department_id"),
            "ward_id": parent_complaint.get("ward_id"),
            "officer_id": parent_complaint.get("officer_id"),
            "status": parent_complaint.get("status"),
            "is_duplicate": True,
            "parent_complaint_id": parent_complaint_id,
            "is_resolved": parent_complaint.get("is_resolved"),
            "location": {
                "lat": final_state["lat"],
                "lon": final_state["lon"],
            },
            "created_at": now,
            "updated_at": now,
        }
    else:
        complaint_doc = {
            "complaint_id": final_state["complaint_id"],
            "user_id": final_state["user_id"],
            "description": final_state["description"],
            "issue_type": final_state["issue_type"],
            "department_id": final_state.get("department_id"),
            "ward_id": final_state.get("ward_id"),
            "officer_id": final_state.get("officer_id"),
            "status": final_state["status"],
            "is_duplicate": False,
            "parent_complaint_id": None,
            "is_resolved": final_state["is_resolved"],
            "issue_confidence": final_state.get("issue_confidence"),
            "rejection_reason": final_state.get("rejection_reason"),
            "location": {
                "lat": final_state["lat"],
                "lon": final_state["lon"],
            },
            "created_at": now,
            "updated_at": now,
        }

    complaints_collection.insert_one(complaint_doc)
    images_collection.insert_one(
        {
            "complaint_id": complaint_doc["complaint_id"],
            "image_url": final_state["image_url"],
            "type": "BEFORE",
            "location": {
                "lat": final_state["lat"],
                "lon": final_state["lon"],
            },
            "created_at": now,
        }
    )
    return complaint_doc, parent_complaint


def _send_assignment_notifications(
    final_state: Dict[str, Any],
    complaint_doc: Dict[str, Any],
    parent_complaint: Optional[Dict[str, Any]],
    parent_complaint_id: Optional[str],
) -> None:
    if final_state.get("status") == "REJECTED":
        return

    if parent_complaint:
        parent_status = parent_complaint.get("status")
        should_notify = parent_status in {"PENDING", "UNRESOLVED"}
        if should_notify and parent_complaint.get("officer_id"):
            try:
                notification_payload = dict(parent_complaint)
                notification_payload["complaint_id"] = parent_complaint_id
                notification_payload["reported_by"] = _resolve_user_name(final_state.get("user_id"))
                parent_image = _find_before_image_url(parent_complaint_id) if parent_complaint_id else None
                create_assignment_notification_and_send(
                    complaint=notification_payload,
                    image_path=parent_image,
                )
            except Exception as exc:
                logger.exception(
                    "Duplicate notification failed parent_complaint_id=%s error=%s",
                    parent_complaint_id,
                    exc,
                )
    elif final_state.get("officer_id"):
        try:
            create_assignment_notification_and_send(
                complaint=complaint_doc,
                image_path=final_state.get("image_url"),
            )
        except Exception as exc:
            logger.exception(
                "Notification initiation failed complaint_id=%s error=%s",
                final_state["complaint_id"],
                exc,
            )


def _build_response_payload(
    complaint_doc: Dict[str, Any],
    parent_complaint: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    effective_department_id = complaint_doc.get("department_id")
    effective_ward_id = complaint_doc.get("ward_id")
    effective_officer_id = complaint_doc.get("officer_id")

    return {
        "complaint_id": complaint_doc["complaint_id"],
        "status": complaint_doc.get("status"),
        "issue_type": complaint_doc.get("issue_type"),
        "issue_confidence": complaint_doc.get("issue_confidence"),
        "rejection_reason": complaint_doc.get("rejection_reason"),
        "has_issue": complaint_doc.get("status") != "REJECTED",
        "department": _get_name_by_id(departments_collection, effective_department_id),
        "ward": _get_name_by_id(wards_collection, effective_ward_id),
        "officer": _resolve_officer_name(effective_officer_id),
        "is_duplicate": complaint_doc.get("is_duplicate"),
        "parent_complaint_id": complaint_doc.get("parent_complaint_id"),
        "parent_status": parent_complaint.get("status") if parent_complaint else None,
        "parent_department": _get_name_by_id(
            departments_collection,
            parent_complaint.get("department_id") if parent_complaint else None,
        )
        if parent_complaint
        else None,
        "parent_ward": _get_name_by_id(
            wards_collection,
            parent_complaint.get("ward_id") if parent_complaint else None,
        )
        if parent_complaint
        else None,
        "parent_officer": _resolve_officer_name(parent_complaint.get("officer_id")) if parent_complaint else None,
    }


def _complaint_owned_by_officer(complaint: Dict[str, Any], officer_id: str) -> bool:
    complaint_officer_id = complaint.get("officer_id")
    if complaint_officer_id is None:
        return False

    if str(complaint_officer_id) == officer_id:
        return True

    try:
        return complaint_officer_id == ObjectId(officer_id)
    except Exception:
        return False


def _run_processing_stream(state: Dict[str, Any]) -> Generator[str, None, None]:
    final_state = dict(state)
    try:
        for chunk in complaint_processing_graph.stream(state):
            for node_name, node_state in chunk.items():
                if isinstance(node_state, dict):
                    final_state.update(node_state)

                step_payload: Dict[str, Any] = {
                    "step": node_name,
                    "message": PROCESSING_STEP_MESSAGES.get(node_name, f"Running {node_name}..."),
                    "status": "running",
                }
                step_payload.update(_enrich_processing_step(node_name, final_state))
                yield format_sse("step", step_payload)
    except ValueError as exc:
        yield format_sse("error", {"message": str(exc)})
        return
    except Exception as exc:
        logger.exception("Graph streaming failed complaint_id=%s error=%s", state.get("complaint_id"), exc)
        yield format_sse("error", {"message": f"Complaint processing failed: {exc}"})
        return

    now = datetime.utcnow()
    try:
        complaint_doc, parent_complaint = _persist_complaint(final_state, now)
        parent_complaint_id = _normalize_complaint_id(parent_complaint) if parent_complaint else None
        _send_assignment_notifications(final_state, complaint_doc, parent_complaint, parent_complaint_id)
        response_payload = _build_response_payload(complaint_doc, parent_complaint)
        yield format_sse("complete", response_payload)
    except HTTPException as exc:
        yield format_sse("error", {"message": exc.detail})
    except Exception as exc:
        logger.exception("Complaint persistence failed complaint_id=%s error=%s", state.get("complaint_id"), exc)
        yield format_sse("error", {"message": f"Failed to save complaint: {exc}"})


def _run_verification_stream(
    complaint: Dict[str, Any],
    complaint_id: str,
    verification_state: Dict[str, Any],
    latitude: float,
    longitude: float,
    after_image_url: str,
    before_image_url: str,
) -> Generator[str, None, None]:
    final_state = dict(verification_state)
    try:
        for chunk in verification_graph.stream(verification_state):
            for node_name, node_state in chunk.items():
                if isinstance(node_state, dict):
                    final_state.update(node_state)

                step_payload: Dict[str, Any] = {
                    "step": node_name,
                    "message": VERIFICATION_STEP_MESSAGES.get(node_name, f"Running {node_name}..."),
                    "status": "running",
                }
                step_payload.update(_enrich_verification_step(node_name, final_state))
                yield format_sse("step", step_payload)
    except ValueError as exc:
        yield format_sse("error", {"message": str(exc)})
        return
    except Exception as exc:
        logger.exception("Verification streaming failed complaint_id=%s error=%s", complaint_id, exc)
        yield format_sse("error", {"message": f"Verification failed: {exc}"})
        return

    location_match = bool(final_state.get("location_match"))
    issue_solved = bool(final_state.get("issue_solved"))
    is_resolved = location_match and issue_solved
    status = "COMPLETED" if is_resolved else "IN_PROGRESS"

    now = datetime.utcnow()
    complaints_collection.update_one(
        {"_id": complaint["_id"]},
        {
            "$set": {
                "is_resolved": is_resolved,
                "status": status,
                "updated_at": now,
                "location": {
                    "lat": latitude,
                    "lon": longitude,
                },
                "before_image_url": before_image_url,
                "after_image_url": after_image_url,
                "location_match": location_match,
                "issue_solved": issue_solved,
            }
        },
    )

    images_collection.insert_one(
        {
            "complaint_id": complaint_id,
            "image_url": after_image_url,
            "type": "AFTER",
            "location": {
                "lat": latitude,
                "lon": longitude,
            },
            "created_at": now,
        }
    )

    yield format_sse(
        "complete",
        {
            "success": True,
            "complaint_id": complaint_id,
            "status": status,
            "is_resolved": is_resolved,
            "location_match": location_match,
            "issue_solved": issue_solved,
            "before_image_url": resolve_public_url(before_image_url),
            "after_image_url": resolve_public_url(after_image_url),
            "message": (
                "Complaint verified and marked as completed"
                if is_resolved
                else "Verification failed — complaint remains in progress"
            ),
        },
    )


@router.post("/complaint")
def create_complaint(
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: UploadFile = File(...),
    user_id: str = Form("anonymous"),
) -> Dict[str, Any]:
    logger.info(
        "Endpoint /complaint started user_id=%s latitude=%s longitude=%s image_name=%s",
        user_id,
        latitude,
        longitude,
        image.filename,
    )

    try:
        image_path = upload_complaint_image(image)
        logger.info("Image saved path=%s", image_path)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Image upload failed error=%s", exc)
        raise HTTPException(status_code=500, detail=f"Image upload failed: {exc}") from exc

    complaint_tracking_id = str(uuid.uuid4())
    state = _build_initial_state(
        complaint_tracking_id,
        user_id,
        description,
        image_path,
        latitude,
        longitude,
    )

    try:
        logger.info("Graph execution started complaint_id=%s", complaint_tracking_id)
        final_state = complaint_processing_graph.invoke(state)
        logger.info("Graph execution completed complaint_id=%s status=%s", complaint_tracking_id, final_state.get("status"))
    except ValueError as exc:
        logger.warning("Graph validation error complaint_id=%s error=%s", complaint_tracking_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Graph execution failed complaint_id=%s error=%s", complaint_tracking_id, exc)
        raise HTTPException(status_code=500, detail=f"Complaint processing failed: {exc}") from exc

    now = datetime.utcnow()
    complaint_doc, parent_complaint = _persist_complaint(final_state, now)
    parent_complaint_id = _normalize_complaint_id(parent_complaint) if parent_complaint else None
    _send_assignment_notifications(final_state, complaint_doc, parent_complaint, parent_complaint_id)

    response_payload = _build_response_payload(complaint_doc, parent_complaint)
    logger.info("Endpoint /complaint completed response=%s", response_payload)
    return response_payload


@router.post("/complaint/stream")
def create_complaint_stream(
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: UploadFile = File(...),
    user_id: str = Form("anonymous"),
) -> StreamingResponse:
    logger.info(
        "Endpoint /complaint/stream started user_id=%s latitude=%s longitude=%s",
        user_id,
        latitude,
        longitude,
    )

    try:
        image_path = upload_complaint_image(image)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Image upload failed error=%s", exc)
        raise HTTPException(status_code=500, detail=f"Image upload failed: {exc}") from exc

    complaint_tracking_id = str(uuid.uuid4())
    state = _build_initial_state(
        complaint_tracking_id,
        user_id,
        description,
        image_path,
        latitude,
        longitude,
    )

    return StreamingResponse(
        _run_processing_stream(state),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/complaints")
def list_complaints(user_id: str) -> Dict[str, Any]:
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    complaints = list(
        complaints_collection.find(_user_id_query(user_id)).sort("created_at", -1)
    )
    items = []
    for complaint in complaints:
        parent = None
        parent_id = complaint.get("parent_complaint_id")
        if complaint.get("is_duplicate") and parent_id:
            parent = _find_complaint_by_reference(parent_id)

        effective = parent or complaint
        effective_status = effective.get("status")
        department_name = _get_name_by_id(departments_collection, effective.get("department_id"))
        ward_name = _get_name_by_id(wards_collection, effective.get("ward_id"))
        officer_name = _resolve_officer_name(effective.get("officer_id"))
        parent_payload = None
        if parent:
            parent_payload = {
                "complaint_id": _normalize_complaint_id(parent),
                "status": parent.get("status"),
                "department": _get_name_by_id(departments_collection, parent.get("department_id")),
                "ward": _get_name_by_id(wards_collection, parent.get("ward_id")),
                "officer": _resolve_officer_name(parent.get("officer_id")),
            }

        items.append(
            {
                "complaint_id": str(complaint.get("complaint_id") or complaint.get("_id")),
                "description": complaint.get("description"),
                "status": effective_status,
                "department": department_name,
                "ward": ward_name,
                "officer": officer_name,
                "image_url": _find_before_image_url(str(complaint.get("complaint_id") or complaint.get("_id"))),
                "is_duplicate": complaint.get("is_duplicate"),
                "created_at": complaint.get("created_at"),
                "updated_at": complaint.get("updated_at"),
                "parent_complaint_id": complaint.get("parent_complaint_id"),
                "parent": parent_payload,
            }
        )

    return {"items": items}


@router.get("/complaint/{complaint_id}/accept")
def accept_complaint(complaint_id: str) -> Dict[str, Any]:
    complaint = complaints_collection.find_one({"complaint_id": complaint_id})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    now = datetime.utcnow()
    complaints_collection.update_one(
        {"_id": complaint["_id"]},
        {
            "$set": {
                "status": "IN_PROGRESS",
                "updated_at": now,
            }
        },
    )
    mark_notification_accepted(complaint_id)

    return {
        "success": True,
        "complaint_id": complaint_id,
        "status": "IN_PROGRESS",
        "message": "Complaint accepted successfully",
    }


@router.post("/complaint/{complaint_id}/resolve")
def resolve_complaint(
    complaint_id: str,
    latitude: float = Form(...),
    longitude: float = Form(...),
    after_image: UploadFile = File(...),
) -> Dict[str, Any]:
    complaint = complaints_collection.find_one({"complaint_id": complaint_id})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    before_image_url = _get_before_image_ref(complaint_id)
    if not before_image_url:
        raise HTTPException(status_code=400, detail="Before image not found for this complaint")

    try:
        after_image_url = upload_complaint_image(after_image)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("After-image upload failed complaint_id=%s error=%s", complaint_id, exc)
        raise HTTPException(status_code=500, detail=f"After-image upload failed: {exc}") from exc

    verification_state = {
        "complaint_id": complaint.get("complaint_id", complaint_id),
        "user_id": complaint.get("user_id", "anonymous"),
        "description": complaint.get("description", ""),
        "image_url": before_image_url,
        "lat": latitude,
        "lon": longitude,
        "issue_type": complaint.get("issue_type"),
        "department_id": complaint.get("department_id"),
        "ward_id": complaint.get("ward_id"),
        "officer_id": complaint.get("officer_id"),
        "is_duplicate": complaint.get("is_duplicate", False),
        "parent_complaint_id": complaint.get("parent_complaint_id"),
        "status": complaint.get("status", "IN_PROGRESS"),
        "is_resolved": complaint.get("is_resolved", False),
        "before_image_url": before_image_url,
        "after_image_url": after_image_url,
        "location_match": None,
        "issue_solved": None,
    }

    try:
        final_state = verification_graph.invoke(verification_state)
    except ValueError as exc:
        logger.warning("Verification validation failed complaint_id=%s error=%s", complaint_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Verification graph failed complaint_id=%s error=%s", complaint_id, exc)
        raise HTTPException(status_code=500, detail=f"Verification failed: {exc}") from exc

    location_match = bool(final_state.get("location_match"))
    issue_solved = bool(final_state.get("issue_solved"))
    is_resolved = location_match and issue_solved
    status = "COMPLETED" if is_resolved else "IN_PROGRESS"

    now = datetime.utcnow()
    complaints_collection.update_one(
        {"_id": complaint["_id"]},
        {
            "$set": {
                "is_resolved": is_resolved,
                "status": status,
                "updated_at": now,
                "location": {
                    "lat": latitude,
                    "lon": longitude,
                },
                "before_image_url": before_image_url,
                "after_image_url": after_image_url,
                "location_match": location_match,
                "issue_solved": issue_solved,
            }
        },
    )

    images_collection.insert_one(
        {
            "complaint_id": complaint_id,
            "image_url": after_image_url,
            "type": "AFTER",
            "location": {
                "lat": latitude,
                "lon": longitude,
            },
            "created_at": now,
        }
    )

    return {
        "success": True,
        "complaint_id": complaint_id,
        "status": status,
        "is_resolved": is_resolved,
        "location_match": location_match,
        "issue_solved": issue_solved,
        "before_image_url": resolve_public_url(before_image_url),
        "after_image_url": resolve_public_url(after_image_url),
    }


@router.post("/complaint/{complaint_id}/resolve/stream")
def resolve_complaint_stream(
    complaint_id: str,
    latitude: float = Form(...),
    longitude: float = Form(...),
    after_image: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(require_role("officer")),
) -> StreamingResponse:
    complaint = complaints_collection.find_one({"complaint_id": complaint_id})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    officer = find_officer_by_user_id(str(current_user["_id"]))
    if not officer:
        raise HTTPException(status_code=404, detail="Officer profile not found")

    if not _complaint_owned_by_officer(complaint, str(officer["_id"])):
        raise HTTPException(status_code=403, detail="Complaint is not assigned to you")

    if complaint.get("status") == "COMPLETED":
        raise HTTPException(status_code=400, detail="Complaint is already completed")

    before_image_url = _get_before_image_ref(complaint_id)
    if not before_image_url:
        raise HTTPException(status_code=400, detail="Before image not found for this complaint")

    try:
        after_image_url = upload_complaint_image(after_image)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("After-image upload failed complaint_id=%s error=%s", complaint_id, exc)
        raise HTTPException(status_code=500, detail=f"After-image upload failed: {exc}") from exc

    verification_state = {
        "complaint_id": complaint.get("complaint_id", complaint_id),
        "user_id": complaint.get("user_id", "anonymous"),
        "description": complaint.get("description", ""),
        "image_url": before_image_url,
        "lat": latitude,
        "lon": longitude,
        "issue_type": complaint.get("issue_type"),
        "department_id": complaint.get("department_id"),
        "ward_id": complaint.get("ward_id"),
        "officer_id": complaint.get("officer_id"),
        "is_duplicate": complaint.get("is_duplicate", False),
        "parent_complaint_id": complaint.get("parent_complaint_id"),
        "status": complaint.get("status", "IN_PROGRESS"),
        "is_resolved": complaint.get("is_resolved", False),
        "before_image_url": before_image_url,
        "after_image_url": after_image_url,
        "location_match": None,
        "issue_solved": None,
    }

    return StreamingResponse(
        _run_verification_stream(
            complaint,
            complaint_id,
            verification_state,
            latitude,
            longitude,
            after_image_url,
            before_image_url,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
