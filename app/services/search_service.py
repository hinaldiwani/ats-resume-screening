"""
app/services/search_service.py

Module 10 — Search & Filter. Two search surfaces:
  - search_resumes: filters the raw resume pool (name, skill, experience
    range) — useful before any screening has happened.
  - search_screening_results: filters already-scored results for the
    requesting recruiter's jobs (name, skill, ATS score range, experience
    range) — this is what powers /screening/results/all.

All filters are optional and combine with AND. Skill filtering joins
through the resume_skills association table; .distinct() guards against
row duplication when a substring search matches more than one of a
resume's skills (e.g. "script" matching both "JavaScript" and
"TypeScript" on the same resume).
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.models import Resume, Candidate, ATSScore, JobDescription, Skill

logger = logging.getLogger(__name__)


def search_resumes(
    db: Session,
    name: Optional[str] = None,
    skill: Optional[str] = None,
    min_experience: Optional[float] = None,
    max_experience: Optional[float] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Resume]:
    query = db.query(Resume).join(Candidate, Resume.candidate_id == Candidate.id)

    if name:
        query = query.filter(Candidate.name.ilike(f"%{name}%"))
    if skill:
        query = query.join(Resume.skills).filter(Skill.name.ilike(f"%{skill}%")).distinct()
    if min_experience is not None:
        query = query.filter(Resume.parsed_experience_years >= min_experience)
    if max_experience is not None:
        query = query.filter(Resume.parsed_experience_years <= max_experience)

    return (
        query.order_by(Resume.uploaded_at.desc(), Resume.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def search_screening_results(
    db: Session,
    recruiter_id: int,
    name: Optional[str] = None,
    skill: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    min_experience: Optional[float] = None,
    max_experience: Optional[float] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[ATSScore]:
    """Scoped to the requesting recruiter's own job postings, matching the
    ownership convention used everywhere else scores are read."""
    job_ids = [
        row[0]
        for row in db.query(JobDescription.id).filter(JobDescription.recruiter_id == recruiter_id).all()
    ]
    if not job_ids:
        return []

    query = (
        db.query(ATSScore)
        .join(Resume, ATSScore.resume_id == Resume.id)
        .join(Candidate, Resume.candidate_id == Candidate.id)
        .filter(ATSScore.job_description_id.in_(job_ids))
    )

    if name:
        query = query.filter(Candidate.name.ilike(f"%{name}%"))
    if skill:
        query = query.join(Resume.skills).filter(Skill.name.ilike(f"%{skill}%")).distinct()
    if min_score is not None:
        query = query.filter(ATSScore.final_score >= min_score)
    if max_score is not None:
        query = query.filter(ATSScore.final_score <= max_score)
    if min_experience is not None:
        query = query.filter(Resume.parsed_experience_years >= min_experience)
    if max_experience is not None:
        query = query.filter(Resume.parsed_experience_years <= max_experience)

    return (
        query.order_by(ATSScore.final_score.desc(), ATSScore.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
