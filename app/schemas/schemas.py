"""
app/schemas/schemas.py
Auth schemas plus the shared APIResponse envelope.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RecruiterRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    company_name: Optional[str] = Field(None, max_length=150)


class RecruiterResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    company_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    access_token: str


class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: str
