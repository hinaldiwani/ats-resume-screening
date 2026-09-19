from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import Job, Candidate, Resume, ScreeningResult, User
from backend.schemas import DashboardStats
from backend.services.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_jobs = db.query(Job).filter(Job.recruiter_id == current_user.id).count()
    total_resumes = (
        db.query(Resume)
        .join(Job, Job.id == Resume.job_id)
        .filter(Job.recruiter_id == current_user.id)
        .count()
    )
    screened_candidates = (
        db.query(ScreeningResult)
        .join(Job, Job.id == ScreeningResult.job_id)
        .filter(Job.recruiter_id == current_user.id)
        .count()
    )
    shortlisted = (
        db.query(ScreeningResult)
        .join(Job, Job.id == ScreeningResult.job_id)
        .filter(Job.recruiter_id == current_user.id, ScreeningResult.status == "Shortlisted")
        .count()
    )
    maybe = (
        db.query(ScreeningResult)
        .join(Job, Job.id == ScreeningResult.job_id)
        .filter(Job.recruiter_id == current_user.id, ScreeningResult.status == "Maybe")
        .count()
    )
    rejected = (
        db.query(ScreeningResult)
        .join(Job, Job.id == ScreeningResult.job_id)
        .filter(Job.recruiter_id == current_user.id, ScreeningResult.status == "Rejected")
        .count()
    )

    avg_score_res = (
        db.query(func.avg(ScreeningResult.overall_score))
        .join(Job, Job.id == ScreeningResult.job_id)
        .filter(Job.recruiter_id == current_user.id)
        .scalar()
    )
    avg_score = round(float(avg_score_res), 1) if avg_score_res is not None else 0.0

    return DashboardStats(
        total_jobs=total_jobs,
        total_resumes=total_resumes,
        screened_candidates=screened_candidates,
        shortlisted_candidates=shortlisted,
        maybe_candidates=maybe,
        rejected_candidates=rejected,
        average_ats_score=avg_score
    )

@router.get("/recent-candidates")
def get_recent_candidates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return top recent screened candidates for the current recruiter."""
    try:
        results = (
            db.query(ScreeningResult)
            .join(Job, Job.id == ScreeningResult.job_id)
            .filter(Job.recruiter_id == current_user.id)
            .order_by(ScreeningResult.created_at.desc())
            .limit(10)
            .all()
        )

        if not results:
            # Fallback: check if any screenings exist across all accessible jobs
            results = db.query(ScreeningResult).order_by(ScreeningResult.created_at.desc()).limit(10).all()

        output = []
        for scr in results:
            cand = db.query(Candidate).filter(Candidate.id == scr.candidate_id).first()
            job = db.query(Job).filter(Job.id == scr.job_id).first()
            output.append({
                "screening_id": scr.id,
                "candidate_id": scr.candidate_id,
                "candidate_name": cand.name if cand else "Candidate",
                "candidate_email": cand.email if cand else "",
                "job_id": scr.job_id,
                "job_title": job.title if job else "Target Role",
                "overall_score": scr.overall_score,
                "skills_score": scr.skills_score,
                "experience_score": scr.experience_score,
                "education_score": scr.education_score,
                "status": scr.status,
                "recommendation": scr.recommendation,
                "detected_experience": scr.detected_experience or "Not detected",
                "detected_education": scr.detected_education or "Not detected",
                "created_at": scr.created_at.isoformat() if scr.created_at else None
            })
        return output
    except Exception as e:
        print(f"Error in get_recent_candidates: {e}")
        return []


