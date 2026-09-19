from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.database import get_db
from backend.models import Candidate, Resume, ScreeningResult, Job, User
from backend.schemas import CandidateResponse
from backend.services.auth import get_current_user

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])

@router.get("", response_model=List[CandidateResponse])
def get_candidates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    candidates = (
        db.query(Candidate)
        .join(Resume, Resume.candidate_id == Candidate.id)
        .join(Job, Job.id == Resume.job_id)
        .filter(Job.recruiter_id == current_user.id)
        .distinct()
        .order_by(Candidate.created_at.desc())
        .all()
    )
    return [CandidateResponse.model_validate(c) for c in candidates]

@router.get("/{candidate_id}", response_model=Dict[str, Any])
def get_candidate_detail(candidate_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    candidate = (
        db.query(Candidate)
        .join(Resume, Resume.candidate_id == Candidate.id)
        .join(Job, Job.id == Resume.job_id)
        .filter(Candidate.id == candidate_id, Job.recruiter_id == current_user.id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    resumes = (
        db.query(Resume)
        .join(Job, Job.id == Resume.job_id)
        .filter(Resume.candidate_id == candidate.id, Job.recruiter_id == current_user.id)
        .all()
    )
    screening_history = []
    for r in resumes:
        scr = db.query(ScreeningResult).filter(ScreeningResult.resume_id == r.id).first()
        job = db.query(Job).filter(Job.id == r.job_id, Job.recruiter_id == current_user.id).first()
        if scr and job:
            screening_history.append({
                "job_id": job.id,
                "job_title": job.title,
                "overall_score": scr.overall_score,
                "skills_score": scr.skills_score,
                "experience_score": scr.experience_score,
                "education_score": scr.education_score,
                "keyword_score": scr.keyword_score,
                "resume_quality_score": scr.resume_quality_score,
                "status": scr.status,
                "recommendation": scr.recommendation,
                "matched_skills": scr.matched_skills_json,
                "missing_skills": scr.missing_skills_json,
                "feedback_summary": scr.feedback_summary,
                "detected_experience": scr.detected_experience or "Not detected",
                "detected_education": scr.detected_education or "Not detected",
                "job_keywords_json": scr.job_keywords_json or "[]",
                "explanation": scr.explanation or scr.feedback_summary or "",
                "created_at": scr.created_at
            })

    return {
        "candidate": CandidateResponse.model_validate(candidate),
        "screening_history": screening_history
    }

