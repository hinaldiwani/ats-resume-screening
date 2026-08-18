"""app/schemas/job_schemas.py"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.skill_schemas import SkillResponse


class JobDescriptionCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=10)
    department: Optional[str] = Field(None, max_length=150)
    min_experience_years: Optional[float] = Field(None, ge=0)
    required_education: Optional[str] = Field(None, max_length=255)
    skills: List[str] = Field(default_factory=list)


class JobStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(open|closed|draft)$")


class JobDescriptionResponse(BaseModel):
    id: int
    recruiter_id: int
    title: str
    description: str
    department: Optional[str] = None
    min_experience_years: Optional[float] = None
    required_education: Optional[str] = None
    status: str
    skills: List[SkillResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
