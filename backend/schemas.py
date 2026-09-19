from pydantic import BaseModel, EmailStr
from typing import List, Optional, Any
from datetime import datetime

# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "Recruiter"

class UserLogin(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Skill Schemas ---
class SkillBase(BaseModel):
    name: str
    category: Optional[str] = "general"

class SkillResponse(SkillBase):
    id: int

    class Config:
        from_attributes = True

# --- Job Schemas ---
class JobCreate(BaseModel):
    title: str
    department: Optional[str] = "Engineering"
    description: str
    required_skills: Optional[List[str]] = []
    preferred_skills: Optional[List[str]] = []
    min_experience: Optional[float] = 0.0
    max_experience: Optional[float] = 10.0
    education: Optional[str] = "Bachelor's Degree"
    location: Optional[str] = "Remote / Hybrid"

class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    education: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None

class JobResponse(BaseModel):
    id: int
    recruiter_id: int
    title: str
    department: str
    description: str
    required_skills_text: Optional[str] = ""
    preferred_skills_text: Optional[str] = ""
    min_experience: float
    max_experience: float
    education: str
    location: str
    status: str
    created_at: datetime
    total_resumes: Optional[int] = 0
    shortlisted_count: Optional[int] = 0

    class Config:
        from_attributes = True

# --- Candidate & Resume Schemas ---
class CandidateResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    education: Optional[str] = None
    experience_years: Optional[float] = None
    raw_resume_text: Optional[str] = ""
    links_json: Optional[str] = "{}"
    created_at: datetime

    class Config:
        from_attributes = True

class ResumeResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    filename: str
    file_type: str
    created_at: datetime
    candidate: Optional[CandidateResponse] = None

    class Config:
        from_attributes = True

# --- Screening Schemas ---
class StatusUpdatePayload(BaseModel):
    status: str # Shortlisted, Maybe, Rejected

class ScreeningResultResponse(BaseModel):
    id: int
    resume_id: int
    job_id: int
    candidate_id: int
    overall_score: float
    skills_score: float
    experience_score: float
    education_score: float
    keyword_score: float
    resume_quality_score: float
    matched_skills_json: Optional[str] = "[]"
    missing_skills_json: Optional[str] = "[]"
    status: str
    recommendation: str
    feedback_summary: Optional[str] = ""
    detected_experience: Optional[str] = "Not detected"
    detected_education: Optional[str] = "Not detected"
    job_keywords_json: Optional[str] = "[]"
    explanation: Optional[str] = ""
    created_at: datetime
    candidate_name: Optional[str] = ""
    candidate_email: Optional[str] = ""
    candidate_phone: Optional[str] = ""

    class Config:
        from_attributes = True

# --- Dashboard Stats Schema ---
class DashboardStats(BaseModel):
    total_jobs: int
    total_resumes: int
    screened_candidates: int
    shortlisted_candidates: int
    maybe_candidates: int
    rejected_candidates: int
    average_ats_score: float
