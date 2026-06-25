import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from models.db import (
    complaints_collection,
    departments_collection,
    images_collection,
    officers_collection,
    wards_collection,
)
from services.auth_service import require_role
from services.officer_service import find_officer_by_user_id, get_officer_user
from services.storage_service import resolve_public_url


router = APIRouter(prefix="/officer", tags=["officer"])
logger = logging.getLogger(__name__)

ALLOWED_STATUS_UPDATES = {"IN_PROGRESS"}


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., min_length=1)


def _to_object_id(value: str) -> Optional[ObjectId]:
    try:
        return ObjectId(value)
    except Exception:
        return None


def _officer_id_query(officer_id: str) -> Dict[str, Any]:
    oid = _to_object_id(officer_id)
    candidates = [officer_id]
    if oid:
        candidates.extend([oid, str(oid)])
    return {"officer_id": {"$in": candidates}}


def _get_name_by_id(collection, object_id_str: Optional[str], field_name: str = "name") -> Optional[str]:
    if not object_id_str:
        return None

    oid = _to_object_id(object_id_str)
    if not oid:
        return None

    doc = collection.find_one({"_id": oid})
    if not doc:
        return None
    return doc.get(field_name)


def _find_before_image_url(complaint_id: str) -> Optional[str]:
    before_image = images_collection.find_one(
        {"complaint_id": complaint_id, "type": "BEFORE"},
        sort=[("created_at", 1)],
    )
    if before_image:
        return resolve_public_url(before_image.get("image_url"))
    return None


def _resolve_officer_name(officer_id: Optional[str]) -> Optional[str]:
    if not officer_id:
        return None

    officer_doc = None
    oid = _to_object_id(officer_id)
    if oid:
        officer_doc = officers_collection.find_one({"_id": oid})
    if not officer_doc:
        officer_doc = officers_collection.find_one({"_id": officer_id})

    if not officer_doc:
        return None

    officer_user = get_officer_user(officer_doc)
    if officer_user:
        return officer_user.get("name")
    return None


def _get_officer_for_user(current_user: Dict[str, Any]) -> Dict[str, Any]:
    officer = find_officer_by_user_id(str(current_user["_id"]))
    if not officer:
        raise HTTPException(status_code=404, detail="Officer profile not found")
    return officer


def _complaint_owned_by_officer(complaint: Dict[str, Any], officer_id: str) -> bool:
    complaint_officer_id = complaint.get("officer_id")
    if complaint_officer_id is None:
        return False

    complaint_officer_str = str(complaint_officer_id)
    if complaint_officer_str == officer_id:
        return True

    oid = _to_object_id(officer_id)
    if oid and complaint_officer_id == oid:
        return True

    return False


def _serialize_complaint(complaint: Dict[str, Any]) -> Dict[str, Any]:
    complaint_id = str(complaint.get("complaint_id") or complaint.get("_id"))
    return {
        "complaint_id": complaint_id,
        "description": complaint.get("description"),
        "status": complaint.get("status"),
        "issue_type": complaint.get("issue_type"),
        "department": _get_name_by_id(departments_collection, complaint.get("department_id")),
        "ward": _get_name_by_id(wards_collection, complaint.get("ward_id")),
        "officer": _resolve_officer_name(complaint.get("officer_id")),
        "image_url": _find_before_image_url(complaint_id),
        "after_image_url": resolve_public_url(complaint.get("after_image_url")),
        "is_resolved": complaint.get("is_resolved"),
        "location_match": complaint.get("location_match"),
        "issue_solved": complaint.get("issue_solved"),
        "location": complaint.get("location"),
        "created_at": complaint.get("created_at"),
        "updated_at": complaint.get("updated_at"),
    }


@router.get("/complaints")
def list_officer_complaints(
    current_user: Dict[str, Any] = Depends(require_role("officer")),
    status: Optional[str] = Query(None, description="Filter by status: PENDING, IN_PROGRESS, COMPLETED"),
    search: Optional[str] = Query(None, description="Search in description, ID, issue type, department, ward"),
) -> Dict[str, List[Dict[str, Any]]]:
    officer = _get_officer_for_user(current_user)
    officer_id = str(officer["_id"])

    complaints = list(
        complaints_collection.find(_officer_id_query(officer_id)).sort("created_at", -1)
    )
    items = [_serialize_complaint(complaint) for complaint in complaints if not complaint.get("is_duplicate")]

    if status:
        normalized_status = status.upper()
        items = [item for item in items if (item.get("status") or "PENDING") == normalized_status]

    if search:
        query = search.strip().lower()
        if query:
            items = [
                item
                for item in items
                if query in (item.get("complaint_id") or "").lower()
                or query in (item.get("description") or "").lower()
                or query in (item.get("issue_type") or "").lower()
                or query in (item.get("department") or "").lower()
                or query in (item.get("ward") or "").lower()
            ]

    logger.info("Officer complaints listed officer_id=%s count=%s", officer_id, len(items))
    return {"items": items}


@router.get("/analytics")
def officer_analytics(
    current_user: Dict[str, Any] = Depends(require_role("officer")),
) -> Dict[str, Any]:
    officer = _get_officer_for_user(current_user)
    officer_id = str(officer["_id"])

    complaints = list(complaints_collection.find(_officer_id_query(officer_id)))
    non_duplicate = [complaint for complaint in complaints if not complaint.get("is_duplicate")]

    status_counts = {"PENDING": 0, "IN_PROGRESS": 0, "COMPLETED": 0}
    issue_type_breakdown: Dict[str, int] = {}
    department_breakdown: Dict[str, int] = {}
    resolution_hours: List[float] = []
    verification_attempts = 0
    verification_passed = 0
    weekly_counts: Dict[str, int] = {}

    now = datetime.utcnow()
    for day_offset in range(6, -1, -1):
        day = (now - timedelta(days=day_offset)).date().isoformat()
        weekly_counts[day] = 0

    for complaint in non_duplicate:
        complaint_status = complaint.get("status") or "PENDING"
        if complaint_status in status_counts:
            status_counts[complaint_status] += 1

        issue_type = complaint.get("issue_type") or "Unknown"
        issue_type_breakdown[issue_type] = issue_type_breakdown.get(issue_type, 0) + 1

        department_name = _get_name_by_id(departments_collection, complaint.get("department_id")) or "Unknown"
        department_breakdown[department_name] = department_breakdown.get(department_name, 0) + 1

        created_at = complaint.get("created_at")
        if isinstance(created_at, datetime):
            created_day = created_at.date().isoformat()
            if created_day in weekly_counts:
                weekly_counts[created_day] += 1

        if complaint.get("after_image_url"):
            verification_attempts += 1
            if complaint.get("is_resolved"):
                verification_passed += 1

        updated_at = complaint.get("updated_at")
        if complaint_status == "COMPLETED" and isinstance(created_at, datetime) and isinstance(updated_at, datetime):
            hours = (updated_at - created_at).total_seconds() / 3600
            if hours >= 0:
                resolution_hours.append(hours)

    total = len(non_duplicate)
    completed = status_counts["COMPLETED"]
    resolution_rate = round((completed / total) * 100, 1) if total else 0.0
    avg_resolution_hours = round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else None
    verification_success_rate = (
        round((verification_passed / verification_attempts) * 100, 1) if verification_attempts else None
    )

    pending_urgent = status_counts["PENDING"]
    active_workload = status_counts["PENDING"] + status_counts["IN_PROGRESS"]

    return {
        "summary": {
            "total": total,
            "pending": status_counts["PENDING"],
            "in_progress": status_counts["IN_PROGRESS"],
            "completed": completed,
            "active_workload": active_workload,
            "pending_urgent": pending_urgent,
            "resolution_rate": resolution_rate,
            "avg_resolution_hours": avg_resolution_hours,
            "verification_success_rate": verification_success_rate,
            "verification_attempts": verification_attempts,
        },
        "by_issue_type": [
            {"name": name, "count": count}
            for name, count in sorted(issue_type_breakdown.items(), key=lambda entry: -entry[1])
        ],
        "by_department": [
            {"name": name, "count": count}
            for name, count in sorted(department_breakdown.items(), key=lambda entry: -entry[1])
        ],
        "weekly_trend": [{"date": day, "count": weekly_counts[day]} for day in sorted(weekly_counts.keys())],
    }


@router.patch("/complaints/{complaint_id}/status")
def update_complaint_status(
    complaint_id: str,
    payload: StatusUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_role("officer")),
) -> Dict[str, Any]:
    new_status = payload.status.upper()
    if new_status not in ALLOWED_STATUS_UPDATES:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {', '.join(sorted(ALLOWED_STATUS_UPDATES))}. "
            "Use the verification flow to mark as COMPLETED.",
        )

    officer = _get_officer_for_user(current_user)
    officer_id = str(officer["_id"])

    complaint = complaints_collection.find_one({"complaint_id": complaint_id})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if not _complaint_owned_by_officer(complaint, officer_id):
        raise HTTPException(status_code=403, detail="Complaint is not assigned to you")

    if complaint.get("status") == "COMPLETED":
        raise HTTPException(status_code=400, detail="Complaint is already completed")

    now = datetime.utcnow()
    complaints_collection.update_one(
        {"_id": complaint["_id"]},
        {"$set": {"status": new_status, "updated_at": now}},
    )

    if new_status == "IN_PROGRESS":
        from services.notification_service import mark_notification_accepted

        mark_notification_accepted(complaint_id)

    return {
        "success": True,
        "complaint_id": complaint_id,
        "status": new_status,
        "message": f"Complaint marked as {new_status.replace('_', ' ').lower()}",
    }
