from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId

from models.db import users_collection
from utils.hash import hash_password, is_password_hash


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _to_object_id(value: Any) -> Optional[ObjectId]:
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def create_user(data: Dict[str, Any]) -> Dict[str, Any]:
    email = _normalize_email(data["email"])
    password = data["password"]
    hashed_password = password if is_password_hash(password) else hash_password(password)

    user = {
        "name": data["name"],
        "email": email,
        "phone": data["phone"],
        "password": hashed_password,
        "role": data["role"],
        "created_at": data.get("created_at") or datetime.utcnow(),
    }
    result = users_collection.insert_one(user)
    user["_id"] = result.inserted_id
    return user


def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    return users_collection.find_one({"email": _normalize_email(email)})


def find_user_by_id(user_id: Any) -> Optional[Dict[str, Any]]:
    oid = _to_object_id(user_id)
    if oid:
        user = users_collection.find_one({"_id": oid})
        if user:
            return user
    return users_collection.find_one({"_id": user_id})
