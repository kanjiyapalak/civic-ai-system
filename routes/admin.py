import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field

from models.db import (
    complaints_collection,
    departments_collection,
    images_collection,
    officers_collection,
    users_collection,
    wards_collection,
)
from services.auth_service import require_role
from services.officer_service import create_officer_user, get_officer_user
from services.storage_service import resolve_public_url


router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


class OfficerCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    phone: str = Field(..., min_length=6)
    password: str = Field(..., min_length=6)
    department_id: str
    ward_id: str


def _to_object_id(value: str) -> Optional[ObjectId]:
    try:
        return ObjectId(value)
    except Exception:
        return None


def _get_name_by_id(collection, object_id_str: Optional[str], field_name: str = "name") -> Optional[str]:
    if not object_id_str:
        return None
    oid = _to_object_id(str(object_id_str))
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


def _resolve_user_name(user_id: Any) -> Optional[str]:
    if not user_id:
        return None
    oid = _to_object_id(str(user_id))
    if oid:
        user = users_collection.find_one({"_id": oid})
        if user:
            return user.get("name")
    user = users_collection.find_one({"_id": user_id})
    return user.get("name") if user else None


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


def _serialize_admin_complaint(complaint: Dict[str, Any]) -> Dict[str, Any]:
    complaint_id = str(complaint.get("complaint_id") or complaint.get("_id"))
    return {
        "complaint_id": complaint_id,
        "description": complaint.get("description"),
        "status": complaint.get("status"),
        "issue_type": complaint.get("issue_type"),
        "citizen": _resolve_user_name(complaint.get("user_id")),
        "department": _get_name_by_id(departments_collection, complaint.get("department_id")),
        "ward": _get_name_by_id(wards_collection, complaint.get("ward_id")),
        "officer": _resolve_officer_name(complaint.get("officer_id")),
        "image_url": _find_before_image_url(complaint_id),
        "after_image_url": resolve_public_url(complaint.get("after_image_url")),
        "is_duplicate": complaint.get("is_duplicate", False),
        "is_resolved": complaint.get("is_resolved"),
        "issue_confidence": complaint.get("issue_confidence"),
        "rejection_reason": complaint.get("rejection_reason"),
        "location": complaint.get("location"),
        "created_at": complaint.get("created_at"),
        "updated_at": complaint.get("updated_at"),
    }


def _serialize_officer(officer: Dict[str, Any]) -> Dict[str, Any]:
    officer_id = str(officer["_id"])
    officer_user = get_officer_user(officer) or {}
    officer_id_query_values = [officer_id]
    oid = _to_object_id(officer_id)
    if oid:
        officer_id_query_values.extend([oid, str(oid)])

    assigned_count = complaints_collection.count_documents(
        {
            "officer_id": {"$in": officer_id_query_values},
            "is_duplicate": {"$ne": True},
            "status": {"$nin": ["REJECTED", "COMPLETED"]},
        }
    )

    return {
        "officer_id": officer_id,
        "user_id": str(officer_user.get("_id") or officer.get("user_id")),
        "name": officer_user.get("name"),
        "email": officer_user.get("email"),
        "phone": officer_user.get("phone"),
        "department": _get_name_by_id(departments_collection, officer.get("department_id")),
        "ward": _get_name_by_id(wards_collection, officer.get("ward_id")),
        "department_id": str(officer.get("department_id")) if officer.get("department_id") else None,
        "ward_id": str(officer.get("ward_id")) if officer.get("ward_id") else None,
        "active_complaints": assigned_count,
        "created_at": officer.get("created_at") or officer_user.get("created_at"),
    }


@router.post("/create-officer", status_code=201)
def create_officer(
    payload: OfficerCreateRequest,
    _: Dict[str, Any] = Depends(require_role("admin")),
) -> Dict[str, Any]:
    return create_officer_user(payload.model_dump())


@router.get("/departments")
def list_departments(
    _: Dict[str, Any] = Depends(require_role("admin")),
) -> Dict[str, Any]:
    departments = list(departments_collection.find({}, {"name": 1}).sort("name", 1))
    return {"items": [{"id": str(dep["_id"]), "name": dep.get("name")} for dep in departments]}


@router.get("/locations/countries")
def list_countries(
    _: Dict[str, Any] = Depends(require_role("admin")),
) -> Dict[str, Any]:
    countries = wards_collection.distinct("country", {"country": {"$exists": True, "$ne": ""}})
    return {"items": sorted(countries)}


@router.get("/locations/states")
def list_states(
    country: str,
    _: Dict[str, Any] = Depends(require_role("admin")),
) -> Dict[str, Any]:
    states = wards_collection.distinct("state", {"country": country, "state": {"$exists": True, "$ne": ""}})
    return {"items": sorted(states)}


@router.get("/locations/cities")
def list_cities(
    country: str,
    state: str,
    _: Dict[str, Any] = Depends(require_role("admin")),
) -> Dict[str, Any]:
    cities = wards_collection.distinct(
        "city",
        {"country": country, "state": state, "city": {"$exists": True, "$ne": ""}},
    )
    return {"items": sorted(cities)}


@router.get("/locations/wards")
def list_wards(
    country: str,
    state: str,
    city: str,
    _: Dict[str, Any] = Depends(require_role("admin")),
) -> Dict[str, Any]:
    wards = list(
        wards_collection.find({"country": country, "state": state, "city": city}, {"name": 1}).sort("name", 1)
    )
    return {"items": [{"id": str(ward["_id"]), "name": ward.get("name")} for ward in wards]}


@router.get("/complaints")
def list_admin_complaints(
    _: Dict[str, Any] = Depends(require_role("admin")),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> Dict[str, List[Dict[str, Any]]]:
    complaints = list(complaints_collection.find().sort("created_at", -1))
    items = [_serialize_admin_complaint(c) for c in complaints if not c.get("is_duplicate")]

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
                or query in (item.get("citizen") or "").lower()
            ]

    return {"items": items}


@router.get("/officers")
def list_admin_officers(
    _: Dict[str, Any] = Depends(require_role("admin")),
    search: Optional[str] = Query(None),
) -> Dict[str, List[Dict[str, Any]]]:
    officers = list(officers_collection.find().sort("created_at", -1))
    items = [_serialize_officer(officer) for officer in officers]

    if search:
        query = search.strip().lower()
        if query:
            items = [
                item
                for item in items
                if query in (item.get("name") or "").lower()
                or query in (item.get("email") or "").lower()
                or query in (item.get("department") or "").lower()
                or query in (item.get("ward") or "").lower()
            ]

    return {"items": items}


@router.get("/analytics")
def admin_analytics(
    _: Dict[str, Any] = Depends(require_role("admin")),
) -> Dict[str, Any]:
    complaints = list(complaints_collection.find())
    non_duplicate = [c for c in complaints if not c.get("is_duplicate")]

    status_counts = {
        "PENDING": 0,
        "IN_PROGRESS": 0,
        "COMPLETED": 0,
        "REJECTED": 0,
        "DUPLICATE": 0,
    }
    issue_breakdown: Dict[str, int] = {}
    department_breakdown: Dict[str, int] = {}
    ward_breakdown: Dict[str, int] = {}
    resolution_hours: List[float] = []
    weekly_counts: Dict[str, int] = {}
    unassigned = 0

    now = datetime.utcnow()
    for day_offset in range(6, -1, -1):
        day = (now - timedelta(days=day_offset)).date().isoformat()
        weekly_counts[day] = 0

    for complaint in non_duplicate:
        complaint_status = complaint.get("status") or "PENDING"
        if complaint_status in status_counts:
            status_counts[complaint_status] += 1
        else:
            status_counts["PENDING"] += 1

        if not complaint.get("officer_id") and complaint_status in {"PENDING", "IN_PROGRESS"}:
            unassigned += 1

        issue_type = complaint.get("issue_type") or "Unknown"
        issue_breakdown[issue_type] = issue_breakdown.get(issue_type, 0) + 1

        dept = _get_name_by_id(departments_collection, complaint.get("department_id")) or "Unassigned"
        department_breakdown[dept] = department_breakdown.get(dept, 0) + 1

        ward = _get_name_by_id(wards_collection, complaint.get("ward_id")) or "Unassigned"
        ward_breakdown[ward] = ward_breakdown.get(ward, 0) + 1

        created_at = complaint.get("created_at")
        if isinstance(created_at, datetime):
            day_key = created_at.date().isoformat()
            if day_key in weekly_counts:
                weekly_counts[day_key] += 1

        updated_at = complaint.get("updated_at")
        if complaint_status == "COMPLETED" and isinstance(created_at, datetime) and isinstance(updated_at, datetime):
            hours = (updated_at - created_at).total_seconds() / 3600
            if hours >= 0:
                resolution_hours.append(hours)

    total = len(non_duplicate)
    completed = status_counts["COMPLETED"]
    active = status_counts["PENDING"] + status_counts["IN_PROGRESS"]
    resolution_rate = round((completed / total) * 100, 1) if total else 0.0
    rejection_rate = round((status_counts["REJECTED"] / total) * 100, 1) if total else 0.0
    avg_resolution_hours = round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else None

    citizen_count = users_collection.count_documents({"role": "citizen"})
    officer_count = officers_collection.count_documents({})
    department_count = departments_collection.count_documents({})
    ward_count = wards_collection.count_documents({})

    return {
        "summary": {
            "total_complaints": total,
            "active": active,
            "pending": status_counts["PENDING"],
            "in_progress": status_counts["IN_PROGRESS"],
            "completed": completed,
            "rejected": status_counts["REJECTED"],
            "unassigned": unassigned,
            "resolution_rate": resolution_rate,
            "rejection_rate": rejection_rate,
            "avg_resolution_hours": avg_resolution_hours,
            "citizens": citizen_count,
            "officers": officer_count,
            "departments": department_count,
            "wards": ward_count,
        },
        "by_issue_type": [
            {"name": name, "count": count}
            for name, count in sorted(issue_breakdown.items(), key=lambda e: -e[1])
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
