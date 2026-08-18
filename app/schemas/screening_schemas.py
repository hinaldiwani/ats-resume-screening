"""app/schemas/screening_schemas.py"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class ScreeningRunRequest(BaseModel):
    resume_id: int
    job_id: int


class ScreeningStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|shortlisted|rejected)$")


class RecommendationResponse(BaseModel):
    id: int
    recommendation_type: str
    message: str
    priority: str
    model_config = ConfigDict(from_attributes=True)


class ATSScoreResponse(BaseModel):
    id: int
    resume_id: int
    job_description_id: int
    semantic_score: float
    skill_match_score: float
    experience_match_score: float
    final_score: float
    status: str
    screened_at: datetime

    matched_skills: List[str] = []
    missing_skills: List[str] = []
    extra_skills: List[str] = []

    recommendations: List[RecommendationResponse] = []

    model_config = ConfigDict(from_attributes=True)
