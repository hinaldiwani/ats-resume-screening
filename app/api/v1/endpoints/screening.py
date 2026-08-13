"""
app/api/v1/endpoints/screening.py

Screening routes: run ATS scoring (single or bulk), retrieve ranked
results for a job, retrieve/update a single result. All protected.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth_dependency import get_current_recruiter
from app.models.models import Recruiter
from app.schemas.schemas import APIResponse
from app.schemas.screening_schemas import ScreeningRunRequest, ScreeningStatusUpdateRequest
from app.services import screening_service, search_service

router = APIRouter()


@router.post("/run", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def run_screening(
    payload: ScreeningRunRequest,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    """Scores one resume against one job. Re-running replaces any existing result for that pair."""
    ats_score = screening_service.run_screening(db, payload.resume_id, payload.job_id)
    return APIResponse(
        success=True,
        data=screening_service.build_ats_score_response(ats_score),
        message="Screening complete.",
    )


@router.post("/run-bulk/{job_id}", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def run_bulk_screening(
    job_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    """Scores every uploaded resume against one job in a single call."""
    results = screening_service.run_bulk_screening(db, job_id)
    return APIResponse(
        success=True,
        data=[screening_service.build_ats_score_response(r) for r in results],
        message=f"Screened {len(results)} resume(s).",
    )


# NOTE ON ROUTE ORDER: /results/all must be declared BEFORE /results/{job_id}.
# FastAPI/Starlette matches routes in registration order, so if the
# parameterized route came first, a request to /results/all would be
# swallowed by it (job_id="all", which then fails int conversion with a
# 422) instead of reaching this handler.
@router.get("/results/all", response_model=APIResponse)
def search_results(
    name: Optional[str] = Query(None, description="Filter by candidate name (substring, case-insensitive)."),
    skill: Optional[str] = Query(None, description="Filter by a required or resume skill (substring, case-insensitive)."),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    min_experience: Optional[float] = Query(None, ge=0),
    max_experience: Optional[float] = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    """
    Module 10 — Search & Filter. All screening results across the
    recruiter's own jobs, with optional filters. Called with no query
    params at all, this is also the route frontend/js/results.js uses to
    populate the results table.
    """
    results = search_service.search_screening_results(
        db, current_recruiter.id,
        name=name, skill=skill,
        min_score=min_score, max_score=max_score,
        min_experience=min_experience, max_experience=max_experience,
        skip=skip, limit=limit,
    )
    return APIResponse(
        success=True,
        data=[screening_service.build_results_list_item(r) for r in results],
        message=f"{len(results)} result(s) found.",
    )


@router.get("/results/{job_id}", response_model=APIResponse)
def get_ranked_results(
    job_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    """Module 8 — Resume Ranking. Existing scores for a job, ranked best-first."""
    results = screening_service.get_ranked_results(db, job_id)
    return APIResponse(
        success=True,
        data=[screening_service.build_ats_score_response(r) for r in results],
        message=f"{len(results)} ranked result(s).",
    )


@router.get("/result/{ats_score_id}", response_model=APIResponse)
def get_screening_result(
    ats_score_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    ats_score = screening_service.get_screening_result(db, ats_score_id)
    return APIResponse(
        success=True,
        data=screening_service.build_ats_score_response(ats_score),
        message="Screening result found.",
    )


@router.patch("/result/{ats_score_id}/status", response_model=APIResponse)
def update_screening_status(
    ats_score_id: int,
    payload: ScreeningStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    ats_score = screening_service.update_screening_status(db, ats_score_id, payload.status)
    return APIResponse(
        success=True,
        data=screening_service.build_ats_score_response(ats_score),
        message=f"Status updated to {payload.status}.",
    )
