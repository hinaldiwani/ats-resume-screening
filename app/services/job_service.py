"""
app/services/job_service.py

Business logic for job descriptions: create (resolving skill name strings
into Skill rows via skill_service), list, get, status updates, and delete.

Read operations (get_job, list_jobs) are open to any authenticated
recruiter — consistent with how resumes and candidates already work in
this project, since there's no organization/team concept tying recruiters
together yet, and hiring is generally a team activity. Mutating operations
(update_job_status, delete_job) are restricted to the recruiter who
created the job.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import JobDescription, Recruiter
from app.schemas.job_schemas import JobDescriptionCreateRequest
from app.services.skill_service import get_or_create_skills

logger = logging.getLogger(__name__)

VALID_JOB_STATUSES = ("open", "closed", "draft")


def create_job(db: Session, recruiter: Recruiter, payload: JobDescriptionCreateRequest) -> JobDescription:
    skills = get_or_create_skills(db, payload.skills)
    job = JobDescription(
        recruiter_id=recruiter.id,
        title=payload.title,
        description=payload.description,
        department=payload.department,
        min_experience_years=payload.min_experience_years,
        required_education=payload.required_education,
        skills=skills,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Created job id=%s title=%s recruiter_id=%s", job.id, job.title, recruiter.id)
    return job


def get_job(db: Session, job_id: int) -> JobDescription:
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found.")
    return job


def list_jobs(
    db: Session,
    recruiter_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[JobDescription]:
    """recruiter_id filters to one recruiter's own postings (used by the ?mine_only=true query param); omit for all jobs."""
    query = db.query(JobDescription)
    if recruiter_id is not None:
        query = query.filter(JobDescription.recruiter_id == recruiter_id)
    return (
        query.order_by(JobDescription.created_at.desc(), JobDescription.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_job_status(db: Session, job_id: int, recruiter_id: int, new_status: str) -> JobDescription:
    job = get_job(db, job_id)
    if job.recruiter_id != recruiter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this job.",
        )
    if new_status not in VALID_JOB_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status value.")
    job.status = new_status
    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job_id: int, recruiter_id: int) -> None:
    job = get_job(db, job_id)
    if job.recruiter_id != recruiter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this job.",
        )
    db.delete(job)
    db.commit()
