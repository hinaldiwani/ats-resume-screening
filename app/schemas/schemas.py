"""
app/schemas/schemas.py

Pydantic schemas for the authentication module. These define the API
contract — what the client must send and what it receives back — and are
kept separate from the SQLAlchemy models in app/models/models.py.
"""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------
class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
class LogoutRequest(BaseModel):
    access_token: str


# ---------------------------------------------------------------------------
# Standard response envelope (matches the convention set in main.py's
# exception handlers, so every response — success or error — has the same shape)
# ---------------------------------------------------------------------------
class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: str
