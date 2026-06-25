from typing import Any, Dict

from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends

from services.auth_service import get_current_user, login_user, signup_user


router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    phone: str = Field(..., min_length=6)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    phone: str
    role: str
    created_at: Any


@router.post("/signup", response_model=UserResponse, status_code=201)
def signup(payload: SignupRequest) -> Dict[str, Any]:
    return signup_user(payload.model_dump())


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    token = login_user(payload.email, payload.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return {
        "user_id": str(current_user.get("_id")),
        "name": current_user.get("name"),
        "email": current_user.get("email"),
        "phone": current_user.get("phone"),
        "role": current_user.get("role"),
        "created_at": current_user.get("created_at"),
    }
