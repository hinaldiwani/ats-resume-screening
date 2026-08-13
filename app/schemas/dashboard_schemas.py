"""
app/schemas/dashboard_schemas.py

NOTE on presentation coupling: the frontend (already built, not modified
as part of this backend work) expects /dashboard/stats to return display
fields — icon class, color tint, trend direction — directly, not just raw
numbers. That's unusual for a REST API; normally the backend wouldn't
decide icon classes. It's done here because the consuming UI is fixed
and already expects this exact shape (see frontend/js/dashboard.js,
DEMO_STATS/DEMO_TOP_CANDIDATES, for the contract this mirrors).
"""

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
    breakdown: Dict[str, float]  # {semantic, skills, experience}


class RecentUploadItem(BaseModel):
    resume_id: int
    candidate_name: str
    candidate_email: str
    file_type: str
    uploaded_at: str
