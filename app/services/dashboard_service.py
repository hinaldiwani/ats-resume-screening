"""
app/services/dashboard_service.py

Module 9 — Dashboard APIs. Three read-only aggregations:
  - get_dashboard_stats: 4 stat tiles (open positions, candidates
    screened, average ATS score, awaiting review), each with a genuine
    "this week" delta computed from real timestamps — not fabricated.
  - get_top_candidates: best-scoring candidates across all of the
    recruiter's jobs combined.
  - get_recent_uploads: most recently uploaded resumes system-wide.

Stats are scoped to the requesting recruiter's own job postings (via
JobDescription.recruiter_id), except total resume count, which is a
system-wide figure since resumes aren't owned by a specific recruiter.

Honesty note on deltas: without a status-change history table, "awaiting
review" can only be given a "new pending items this week" delta (always
>= 0) rather than a true net change — a decrease can't be computed
without knowing when items left the pending state. Documented inline
rather than fabricating a number.
"""

import logging
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import JobDescription, ATSScore, Resume

logger = logging.getLogger(__name__)

WEEK_AGO = lambda: datetime.utcnow() - timedelta(days=7)  # noqa: E731


def _recruiter_job_ids(db: Session, recruiter_id: int) -> List[int]:
    return [row[0] for row in db.query(JobDescription.id).filter(JobDescription.recruiter_id == recruiter_id).all()]


def get_dashboard_stats(db: Session, recruiter_id: int) -> List[dict]:
    job_ids = _recruiter_job_ids(db, recruiter_id)
    week_ago = WEEK_AGO()

    # --- Open positions ---
    open_positions = (
        db.query(JobDescription)
        .filter(JobDescription.recruiter_id == recruiter_id, JobDescription.status == "open")
        .count()
    )
    new_jobs_this_week = (
        db.query(JobDescription)
        .filter(JobDescription.recruiter_id == recruiter_id, JobDescription.created_at >= week_ago)
        .count()
    )

    if not job_ids:
        candidates_screened = 0
        new_screened_this_week = 0
        avg_score = None
        avg_score_prior = None
        awaiting_review = 0
        new_pending_this_week = 0
    else:
        candidates_screened = db.query(ATSScore).filter(ATSScore.job_description_id.in_(job_ids)).count()
        new_screened_this_week = (
            db.query(ATSScore)
            .filter(ATSScore.job_description_id.in_(job_ids), ATSScore.screened_at >= week_ago)
            .count()
        )

        avg_score = (
            db.query(func.avg(ATSScore.final_score))
            .filter(ATSScore.job_description_id.in_(job_ids))
            .scalar()
        )
        avg_score_prior = (
            db.query(func.avg(ATSScore.final_score))
            .filter(ATSScore.job_description_id.in_(job_ids), ATSScore.screened_at < week_ago)
            .scalar()
        )

        awaiting_review = (
            db.query(ATSScore)
            .filter(ATSScore.job_description_id.in_(job_ids), ATSScore.status == "pending")
            .count()
        )
        new_pending_this_week = (
            db.query(ATSScore)
            .filter(
                ATSScore.job_description_id.in_(job_ids),
                ATSScore.status == "pending",
                ATSScore.screened_at >= week_ago,
            )
            .count()
        )

    avg_score_display = round(avg_score, 1) if avg_score is not None else 0.0
    score_delta = (
        round(avg_score - avg_score_prior, 1)
        if avg_score is not None and avg_score_prior is not None
        else 0.0
    )
    score_tint = "score-good" if avg_score_display >= 75 else "score-mid" if avg_score_display >= 50 else "score-low"
    review_tint = "score-good" if awaiting_review == 0 else "score-mid"

    return [
        {
            "label": "Open positions",
            "value": str(open_positions),
            "icon": "bi-briefcase",
            "tint": "score-good",
            "delta": f"+{new_jobs_this_week} this week",
            "up": True,
        },
        {
            "label": "Candidates screened",
            "value": str(candidates_screened),
            "icon": "bi-people",
            "tint": "score-mid",
            "delta": f"+{new_screened_this_week} this week",
            "up": True,
        },
        {
            "label": "Avg. match score",
            "value": str(avg_score_display),
            "icon": "bi-graph-up-arrow",
            "tint": score_tint,
            "delta": f"{'+' if score_delta >= 0 else ''}{score_delta} pts",
            "up": score_delta >= 0,
        },
        {
            "label": "Awaiting review",
            "value": str(awaiting_review),
            "icon": "bi-hourglass-split",
            "tint": review_tint,
            "delta": f"+{new_pending_this_week} this week",
            "up": True,
        },
    ]


def get_top_candidates(db: Session, recruiter_id: int, limit: int = 5) -> List[dict]:
    """Best-scoring candidates across all of the recruiter's jobs combined, matching the
    {name, role, score, breakdown} shape frontend/js/dashboard.js already expects."""
    job_ids = _recruiter_job_ids(db, recruiter_id)
    if not job_ids:
        return []

    scores = (
        db.query(ATSScore)
        .filter(ATSScore.job_description_id.in_(job_ids))
        .order_by(ATSScore.final_score.desc(), ATSScore.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "name": s.resume.candidate.name,
            "role": s.job_description.title,
            "score": s.final_score,
            "breakdown": {
                "semantic": s.semantic_score,
                "skills": s.skill_match_score,
                "experience": s.experience_match_score,
            },
        }
        for s in scores
    ]


def get_recent_uploads(db: Session, limit: int = 10) -> List[dict]:
    """Most recently uploaded resumes system-wide (resumes aren't owned by a specific recruiter)."""
    resumes = (
        db.query(Resume)
        .order_by(Resume.uploaded_at.desc(), Resume.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "resume_id": r.id,
            "candidate_name": r.candidate.name,
            "candidate_email": r.candidate.email,
            "file_type": r.file_type,
            "uploaded_at": r.uploaded_at.isoformat(),
        }
        for r in resumes
    ]
