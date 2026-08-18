"""app/schemas/dashboard_schemas.py"""
from typing import Dict
from pydantic import BaseModel


class DashboardStatItem(BaseModel):
    label: str
    value: str
    icon: str
    tint: str
    delta: str
    up: bool


class TopCandidateItem(BaseModel):
    name: str
    role: str
    score: float
    breakdown: Dict[str, float]


class RecentUploadItem(BaseModel):
    resume_id: int
    candidate_name: str
    candidate_email: str
    file_type: str
    uploaded_at: str
