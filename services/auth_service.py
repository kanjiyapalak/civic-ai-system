from datetime import datetime
from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from bson import ObjectId

from models.db import departments_collection, wards_collection
from models.officer import create_officer
from models.user_model import create_user, find_user_by_email, find_user_by_id
from utils.hash import verify_password
from utils.jwt import create_access_token, verify_token


security = HTTPBearer(auto_error=False)


def _user_response(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(user.get("_id")),
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "role": user.get("role"),
        "created_at": user.get("created_at"),
    }


def signup_user(payload: Dict[str, Any]) -> Dict[str, Any]:
    email = payload["email"].strip().lower()
    if find_user_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = create_user(
        {
            "name": payload["name"],
            "email": email,
            "phone": payload["phone"],
            "password": payload["password"],
            "role": "citizen",
            "created_at": datetime.utcnow(),
        }
    )
    return _user_response(user)


def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    user = find_user_by_email(email)
    if not user or not verify_password(password, user.get("password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return user


def login_user(email: str, password: str) -> str:
    user = authenticate_user(email, password)
    return create_access_token({"user_id": str(user["_id"]), "role": user.get("role")})


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

    response = _user_response(user)
    response.update(
        {
            "officer_id": str(officer_result.inserted_id),
            "department_id": department_id,
            "ward_id": ward_id,
        }
    )
    return response


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    try:
        payload = verify_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def require_role(*roles: str):
    def dependency(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if current_user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user

    return dependency
