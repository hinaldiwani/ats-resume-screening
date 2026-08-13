"""
app/api/v1/endpoints/jobs.py

Job description CRUD routes. All protected. Reads are open to any
authenticated recruiter; status updates and deletion are restricted to
the job's creator (enforced in job_service.py, not here, so the
ownership rule lives in one place).
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth_dependency import get_current_recruiter
from app.models.models import Recruiter
from app.schemas.job_schemas import (
    JobDescriptionCreateRequest,
    JobDescriptionResponse,
    JobStatusUpdateRequest,
)
from app.schemas.schemas import APIResponse
from app.services import job_service

router = APIRouter()


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobDescriptionCreateRequest,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    job = job_service.create_job(db, current_recruiter, payload)
    return APIResponse(
        success=True,
        data=JobDescriptionResponse.model_validate(job).model_dump(mode="json"),
        message="Job description created successfully.",
    )


@router.get("/", response_model=APIResponse)
def list_jobs(
    mine_only: bool = Query(False, description="If true, only return jobs created by the current recruiter."),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    recruiter_filter: Optional[int] = current_recruiter.id if mine_only else None
    jobs = job_service.list_jobs(db, recruiter_id=recruiter_filter, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        data=[JobDescriptionResponse.model_validate(j).model_dump(mode="json") for j in jobs],
        message=f"{len(jobs)} job(s) found.",
    )


@router.get("/{job_id}", response_model=APIResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    job = job_service.get_job(db, job_id)
    return APIResponse(
        success=True,
        data=JobDescriptionResponse.model_validate(job).model_dump(mode="json"),
        message="Job description found.",
    )


@router.patch("/{job_id}/status", response_model=APIResponse)
def update_job_status(
    job_id: int,
    payload: JobStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    job = job_service.update_job_status(db, job_id, current_recruiter.id, payload.status)
    return APIResponse(
        success=True,
        data=JobDescriptionResponse.model_validate(job).model_dump(mode="json"),
        message=f"Job status updated to {payload.status}.",
    )


@router.delete("/{job_id}", response_model=APIResponse)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    job_service.delete_job(db, job_id, current_recruiter.id)
    return APIResponse(success=True, data=None, message="Job description deleted successfully.")
