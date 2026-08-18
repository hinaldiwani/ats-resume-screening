"""app/schemas/candidate_schemas.py"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CandidateCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=30)
    location: Optional[str] = Field(None, max_length=150)


class CandidateResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
