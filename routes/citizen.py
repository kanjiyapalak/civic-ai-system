import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from models.db import (
    complaints_collection,
    departments_collection,
    images_collection,
    officers_collection,
    wards_collection,
)
from services.auth_service import require_role
from services.officer_service import get_officer_user
from services.storage_service import resolve_public_url


router = APIRouter(prefix="/citizen", tags=["citizen"])
logger = logging.getLogger(__name__)


def _to_object_id(value: str) -> Optional[ObjectId]:
    try:
        return ObjectId(value)
    except Exception:
        return None


def _user_id_query(user_id: str) -> Dict[str, Any]:
    oid = _to_object_id(user_id)
    if oid:
        return {"user_id": {"$in": [user_id, oid]}}
    return {"user_id": user_id}


def _get_name_by_id(collection, object_id_str: Optional[str], field_name: str = "name") -> Optional[str]:
    if not object_id_str:
        return None
    oid = _to_object_id(object_id_str)
    if not oid:
        return None
    doc = collection.find_one({"_id": oid})
    return doc.get(field_name) if doc else None


def _find_before_image_url(complaint_id: str) -> Optional[str]:
    before_image = images_collection.find_one(
        {"complaint_id": complaint_id, "type": "BEFORE"},
        sort=[("created_at", 1)],
    )
    return resolve_public_url(before_image.get("image_url")) if before_image else None


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


def _normalize_complaint_id(complaint: Dict[str, Any]) -> Optional[str]:
    if not complaint:
        return None
    return str(complaint.get("complaint_id") or complaint.get("_id"))


def _resolve_officer_name(officer_id: Optional[str]) -> Optional[str]:
    if not officer_id:
        return None
    officer_doc = None
    oid = _to_object_id(str(officer_id))
    if oid:
        officer_doc = officers_collection.find_one({"_id": oid})
    if not officer_doc:
        officer_doc = officers_collection.find_one({"_id": officer_id})
    if not officer_doc:
        return None
    officer_user = get_officer_user(officer_doc)
    return officer_user.get("name") if officer_user else None


def _serialize_citizen_complaint(complaint: Dict[str, Any]) -> Dict[str, Any]:
    complaint_id = _normalize_complaint_id(complaint)
    parent = None
    parent_id = complaint.get("parent_complaint_id")
    if complaint.get("is_duplicate") and parent_id:
        parent = _find_complaint_by_reference(parent_id)

    effective = parent or complaint
    effective_status = effective.get("status")

    parent_payload = None
    if parent:
        parent_payload = {
            "complaint_id": _normalize_complaint_id(parent),
            "status": parent.get("status"),
            "department": _get_name_by_id(departments_collection, parent.get("department_id")),
            "ward": _get_name_by_id(wards_collection, parent.get("ward_id")),
            "officer": _resolve_officer_name(parent.get("officer_id")),
        }

    return {
        "complaint_id": complaint_id,
        "description": complaint.get("description"),
        "status": effective_status,
        "issue_type": effective.get("issue_type") or complaint.get("issue_type"),
        "department": _get_name_by_id(departments_collection, effective.get("department_id")),
        "ward": _get_name_by_id(wards_collection, effective.get("ward_id")),
        "officer": _resolve_officer_name(effective.get("officer_id")),
        "image_url": _find_before_image_url(complaint_id) if complaint_id else None,
        "after_image_url": resolve_public_url(effective.get("after_image_url")),
        "is_duplicate": complaint.get("is_duplicate", False),
        "is_resolved": effective.get("is_resolved"),
        "location_match": effective.get("location_match"),
        "issue_solved": effective.get("issue_solved"),
        "created_at": complaint.get("created_at"),
        "updated_at": effective.get("updated_at") or complaint.get("updated_at"),
        "parent_complaint_id": complaint.get("parent_complaint_id"),
        "parent": parent_payload,
        "issue_confidence": complaint.get("issue_confidence"),
        "rejection_reason": complaint.get("rejection_reason"),
    }


def _fetch_citizen_complaints(user_id: str) -> List[Dict[str, Any]]:
    complaints = list(complaints_collection.find(_user_id_query(user_id)).sort("created_at", -1))
    return [_serialize_citizen_complaint(complaint) for complaint in complaints]


@router.get("/complaints")
def list_citizen_complaints(
    current_user: Dict[str, Any] = Depends(require_role("citizen")),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search complaints"),
) -> Dict[str, List[Dict[str, Any]]]:
    user_id = str(current_user["_id"])
    items = _fetch_citizen_complaints(user_id)

    if status:
        normalized = status.upper()
        items = [item for item in items if (item.get("status") or "PENDING") == normalized]

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
                or query in (item.get("officer") or "").lower()
            ]

    logger.info("Citizen complaints listed user_id=%s count=%s", user_id, len(items))
    return {"items": items}


@router.get("/analytics")
def citizen_analytics(
    current_user: Dict[str, Any] = Depends(require_role("citizen")),
) -> Dict[str, Any]:
    user_id = str(current_user["_id"])
    items = _fetch_citizen_complaints(user_id)

    status_counts = {"PENDING": 0, "IN_PROGRESS": 0, "COMPLETED": 0, "DUPLICATE": 0, "REJECTED": 0}
    issue_type_breakdown: Dict[str, int] = {}
    department_breakdown: Dict[str, int] = {}
    ward_breakdown: Dict[str, int] = {}
    resolution_hours: List[float] = []
    duplicate_count = 0
    weekly_counts: Dict[str, int] = {}

    now = datetime.utcnow()
    for day_offset in range(6, -1, -1):
        day = (now - timedelta(days=day_offset)).date().isoformat()
        weekly_counts[day] = 0

    for item in items:
        complaint_status = item.get("status") or "PENDING"
        if complaint_status in status_counts:
            status_counts[complaint_status] += 1
        else:
            status_counts["PENDING"] += 1

        if item.get("is_duplicate"):
            duplicate_count += 1

        issue_type = item.get("issue_type") or "Unknown"
        issue_type_breakdown[issue_type] = issue_type_breakdown.get(issue_type, 0) + 1

        department = item.get("department") or "Unassigned"
        department_breakdown[department] = department_breakdown.get(department, 0) + 1

        ward = item.get("ward") or "Unassigned"
        ward_breakdown[ward] = ward_breakdown.get(ward, 0) + 1

        created_at = item.get("created_at")
        if isinstance(created_at, datetime):
            created_day = created_at.date().isoformat()
            if created_day in weekly_counts:
                weekly_counts[created_day] += 1

        updated_at = item.get("updated_at")
        if complaint_status == "COMPLETED" and isinstance(created_at, datetime) and isinstance(updated_at, datetime):
            hours = (updated_at - created_at).total_seconds() / 3600
            if hours >= 0:
                resolution_hours.append(hours)

    total = len(items)
    completed = status_counts["COMPLETED"]
    active = status_counts["PENDING"] + status_counts["IN_PROGRESS"]
    resolution_rate = round((completed / total) * 100, 1) if total else 0.0
    avg_resolution_hours = round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else None

    return {
        "summary": {
            "total": total,
            "pending": status_counts["PENDING"],
            "in_progress": status_counts["IN_PROGRESS"],
            "completed": completed,
            "active": active,
            "duplicates": duplicate_count,
            "rejected": status_counts["REJECTED"],
            "resolution_rate": resolution_rate,
            "avg_resolution_hours": avg_resolution_hours,
        },
        "by_issue_type": [
            {"name": name, "count": count}
            for name, count in sorted(issue_type_breakdown.items(), key=lambda e: -e[1])
        ],
        "by_department": [
            {"name": name, "count": count}
            for name, count in sorted(department_breakdown.items(), key=lambda e: -e[1])
        ],
        "by_ward": [
            {"name": name, "count": count}
            for name, count in sorted(ward_breakdown.items(), key=lambda e: -e[1])
        ],
        "weekly_trend": [{"date": day, "count": weekly_counts[day]} for day in sorted(weekly_counts.keys())],
    }
