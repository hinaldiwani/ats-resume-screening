"""
app/api/v1/endpoints/resumes.py

Resume upload and retrieval routes. Upload accepts multipart/form-data
(a file plus optional candidate_name/candidate_email fields); all routes
are protected — only authenticated recruiters can upload or view resumes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth_dependency import get_current_recruiter
from app.models.models import Recruiter
from app.schemas.resume_schemas import ResumeResponse
from app.schemas.schemas import APIResponse
from app.services import resume_service, search_service

router = APIRouter()


@router.post("/upload", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile = File(...),
    candidate_name: Optional[str] = Form(None),
    candidate_email: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    """
    Accepts a PDF or DOCX resume upload. candidate_name/candidate_email are
    optional — if omitted, the values extracted from the resume text itself
    are used to link (or create) the candidate record. Runs the full
    parse pipeline synchronously and returns the structured result.
    """
    resume = resume_service.upload_resume(
        db, file, candidate_name=candidate_name, candidate_email=candidate_email
    )
    return APIResponse(
        success=True,
        data=ResumeResponse.model_validate(resume).model_dump(mode="json"),
        message="Resume uploaded and parsed successfully.",
    )


@router.get("/{resume_id}", response_model=APIResponse)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    resume = resume_service.get_resume(db, resume_id)
    return APIResponse(
        success=True,
        data=ResumeResponse.model_validate(resume).model_dump(mode="json"),
        message="Resume found.",
    )


@router.get("/candidate/{candidate_id}", response_model=APIResponse)
def list_resumes_by_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    resumes = resume_service.list_resumes_by_candidate(db, candidate_id)
    return APIResponse(
        success=True,
        data=[ResumeResponse.model_validate(r).model_dump(mode="json") for r in resumes],
        message=f"{len(resumes)} resume(s) found.",
    )


@router.get("/", response_model=APIResponse)
def list_resumes(
    name: Optional[str] = Query(None, description="Filter by candidate name (substring, case-insensitive)."),
    skill: Optional[str] = Query(None, description="Filter by resume skill (substring, case-insensitive)."),
    min_experience: Optional[float] = Query(None, ge=0),
    max_experience: Optional[float] = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    """Module 10 — Search & Filter applies here too: called with no filters, behaves exactly
    as the plain resume listing did before; any filter present narrows the results."""
    resumes = search_service.search_resumes(
        db, name=name, skill=skill,
        min_experience=min_experience, max_experience=max_experience,
        skip=skip, limit=limit,
    )
    return APIResponse(
        success=True,
        data=[ResumeResponse.model_validate(r).model_dump(mode="json") for r in resumes],
        message=f"{len(resumes)} resume(s) found.",
    )
