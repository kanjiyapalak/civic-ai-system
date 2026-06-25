from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from bson import ObjectId

from models.db import departments_collection, officers_collection, users_collection, wards_collection
from models.officer import create_officer
from models.user_model import create_user, find_user_by_email


def _to_object_id(value: str) -> Optional[ObjectId]:
    try:
        return ObjectId(value)
    except Exception:
        return None


def find_assignable_officer(department_id: str, ward_id: str) -> Optional[Dict[str, Any]]:
    queries = [{"department_id": department_id, "ward_id": ward_id}]

    dep_oid = _to_object_id(department_id)
    ward_oid = _to_object_id(ward_id)
    if dep_oid and ward_oid:
        queries.append({"department_id": dep_oid, "ward_id": ward_oid})

    for query in queries:
        officer = officers_collection.find_one(query)
        if officer:
            return officer

    return None


def _require_department(department_id: str) -> None:
    dep_oid = None
    try:
        dep_oid = ObjectId(department_id)
    except Exception:
        dep_oid = None

    if dep_oid:
        if departments_collection.find_one({"_id": dep_oid}):
            return

    if departments_collection.find_one({"_id": department_id}):
        return

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department not found")


def _require_ward(ward_id: str) -> str:
    if not ward_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ward is required")

    try:
        ward_oid = ObjectId(ward_id)
    except Exception:
        ward_oid = None

    if ward_oid:
        if wards_collection.find_one({"_id": ward_oid}):
            return ward_id

    if wards_collection.find_one({"_id": ward_id}):
        return ward_id

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ward not found")


def create_officer_user(payload: Dict[str, Any]) -> Dict[str, Any]:
    email = payload["email"].strip().lower()
    if find_user_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    department_id = payload.get("department_id")
    ward_id = payload.get("ward_id")
    if not department_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department is required")

    _require_department(department_id)
    ward_id = _require_ward(ward_id)

    user = create_user(
        {
            "name": payload["name"],
            "email": email,
            "phone": payload["phone"],
            "password": payload["password"],
            "role": "officer",
            "created_at": datetime.utcnow(),
        }
    )
    officer_result = create_officer(
        {
            "user_id": user["_id"],
            "department_id": department_id,
            "ward_id": ward_id,
        }
    )

    return {
        "user_id": str(user.get("_id")),
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "role": user.get("role"),
        "created_at": user.get("created_at"),
        "officer_id": str(officer_result.inserted_id),
        "department_id": department_id,
        "ward_id": ward_id,
    }


def find_officer_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    oid = _to_object_id(user_id)
    if oid:
        officer = officers_collection.find_one({"user_id": oid})
        if officer:
            return officer

    return officers_collection.find_one({"user_id": user_id})


def get_officer_user(officer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    user_id = officer.get("user_id")
    if user_id is None:
        return None

    if isinstance(user_id, ObjectId):
        return users_collection.find_one({"_id": user_id})

    oid = _to_object_id(str(user_id))
    if oid:
        return users_collection.find_one({"_id": oid})

    return users_collection.find_one({"_id": user_id})
