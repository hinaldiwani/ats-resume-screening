"""
app/api/v1/endpoints/candidates.py

Candidate CRUD routes. All protected — only authenticated recruiters can
view or create candidate records.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth_dependency import get_current_recruiter
from app.models.models import Recruiter
from app.schemas.candidate_schemas import CandidateCreateRequest, CandidateResponse
from app.schemas.schemas import APIResponse
from app.services import candidate_service

router = APIRouter()


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreateRequest,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    """Registers a candidate directly (as opposed to auto-creation via resume upload)."""
    candidate = candidate_service.create_candidate(db, payload)
    return APIResponse(
        success=True,
        data=CandidateResponse.model_validate(candidate).model_dump(mode="json"),
        message="Candidate created successfully.",
    )


@router.get("/", response_model=APIResponse)
def list_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    candidates = candidate_service.list_candidates(db, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        data=[CandidateResponse.model_validate(c).model_dump(mode="json") for c in candidates],
        message=f"{len(candidates)} candidate(s) found.",
    )


@router.get("/{candidate_id}", response_model=APIResponse)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    candidate = candidate_service.get_candidate(db, candidate_id)
    return APIResponse(
        success=True,
        data=CandidateResponse.model_validate(candidate).model_dump(mode="json"),
        message="Candidate found.",
    )
