from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.database import get_db
from backend.models import Job, Candidate, Resume, ScreeningResult, User
from backend.schemas import ScreeningResultResponse, StatusUpdatePayload
from backend.services.auth import get_current_user

router = APIRouter(prefix="/api/screening", tags=["Screening & Candidate Ranking"])

@router.get("/all", response_model=List[ScreeningResultResponse])
def get_all_screening_results(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all screened candidates across all jobs for current recruiter."""
    query = (
        db.query(ScreeningResult)
        .join(Job, Job.id == ScreeningResult.job_id)
        .filter(Job.recruiter_id == current_user.id)
    )
    if status_filter and status_filter.lower() != "all":
        query = query.filter(ScreeningResult.status == status_filter)

    results = query.order_by(ScreeningResult.overall_score.desc()).all()
    output = []
    for r in results:
        cand = db.query(Candidate).filter(Candidate.id == r.candidate_id).first()
        resp = ScreeningResultResponse.model_validate(r)
        if cand:
            resp.candidate_name = cand.name
            resp.candidate_email = cand.email
            resp.candidate_phone = cand.phone
            if not resp.detected_experience:
                resp.detected_experience = f"{cand.experience_years:g} years" if (cand.experience_years is not None and cand.experience_years > 0) else "Not detected"
            if not resp.detected_education:
                resp.detected_education = cand.education or "Not detected"
        output.append(resp)
    return output

@router.get("/job/{job_id}", response_model=List[ScreeningResultResponse])
def get_job_screening_results(
    job_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or access denied")

    query = db.query(ScreeningResult).filter(ScreeningResult.job_id == job_id)

    if status_filter and status_filter.lower() != "all":
        query = query.filter(ScreeningResult.status == status_filter)

    results = query.order_by(ScreeningResult.overall_score.desc()).all()

    output = []
    for r in results:
        cand = db.query(Candidate).filter(Candidate.id == r.candidate_id).first()
        resp = ScreeningResultResponse.model_validate(r)
        if cand:
            resp.candidate_name = cand.name
            resp.candidate_email = cand.email
            resp.candidate_phone = cand.phone
            if not resp.detected_experience:
                resp.detected_experience = f"{cand.experience_years:g} years" if (cand.experience_years is not None and cand.experience_years > 0) else "Not detected"
            if not resp.detected_education:
                resp.detected_education = cand.education or "Not detected"
        output.append(resp)

    return output

@router.patch("/{screening_id}/status", response_model=ScreeningResultResponse)
def update_candidate_status(
    screening_id: int,
    payload: StatusUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scr = (
        db.query(ScreeningResult)
        .join(Job, Job.id == ScreeningResult.job_id)
        .filter(ScreeningResult.id == screening_id, Job.recruiter_id == current_user.id)
        .first()
    )
    if not scr:
        raise HTTPException(status_code=404, detail="Screening result not found or access denied")

    valid_statuses = ["Shortlisted", "Maybe", "Rejected"]
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    scr.status = payload.status
    db.commit()
    db.refresh(scr)

    cand = db.query(Candidate).filter(Candidate.id == scr.candidate_id).first()
    resp = ScreeningResultResponse.model_validate(scr)
    if cand:
        resp.candidate_name = cand.name
        resp.candidate_email = cand.email
        resp.candidate_phone = cand.phone
        if not resp.detected_experience:
            resp.detected_experience = f"{cand.experience_years:g} years" if (cand.experience_years is not None and cand.experience_years > 0) else "Not detected"
        if not resp.detected_education:
            resp.detected_education = cand.education or "Not detected"

    return resp
