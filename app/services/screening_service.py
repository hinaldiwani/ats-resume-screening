"""
app/services/screening_service.py

Module 7/8 orchestration:
  - run_screening: scores one resume against one job (scoring_service.py
    does the math), persists an ATSScore row, and generates explanatory
    Recommendation rows from the result.
  - run_bulk_screening: runs screening for every resume against one job.
  - get_ranked_results: Module 8, Resume Ranking — existing scores for a
    job ordered by final_score desc, with tiebreakers.
  - Status updates and single-result retrieval for the endpoints.

Re-running screening for the same resume/job pair replaces the existing
ATSScore rather than duplicating it, so results always reflect current
resume/job data instead of accumulating stale rows.
"""

import logging
from typing import List

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import Resume, JobDescription, ATSScore, Recommendation
from app.services import scoring_service

logger = logging.getLogger(__name__)

VALID_STATUSES = ("pending", "shortlisted", "rejected")


def _generate_recommendations(
    db: Session, ats_score: ATSScore, score_result: dict, job: JobDescription, resume: Resume
) -> None:
    """
    Builds explanatory Recommendation rows from a scoring result — this is
    what makes a score auditable instead of a black-box number (see
    architecture doc, §13). Kept as a private helper here rather than a
    separate service module since it's tightly coupled to this one call
    site and not reused elsewhere.
    """
    recommendations = []

    if score_result["missing_skills"]:
        skill_pct = score_result["skill_match_score"]
        priority = "high" if skill_pct < 50 else "medium" if skill_pct < 80 else "low"
        skills_list = ", ".join(score_result["missing_skills"])
        recommendations.append(Recommendation(
            ats_score=ats_score,
            recommendation_type="missing_skill",
            message=f"Missing skill(s): {skills_list}.",
            priority=priority,
        ))

    if job.min_experience_years and score_result["experience_match_score"] < 100:
        exp_priority = "high" if score_result["experience_match_score"] < 50 else "medium"
        if resume.parsed_experience_years is None:
            exp_message = (
                f"Could not confirm years of experience from the resume; "
                f"role requires {job.min_experience_years} years."
            )
        else:
            exp_message = (
                f"{resume.parsed_experience_years} years of experience found; "
                f"role requires {job.min_experience_years} years."
            )
        recommendations.append(Recommendation(
            ats_score=ats_score, recommendation_type="experience_gap",
            message=exp_message, priority=exp_priority,
        ))

    if job.required_education and not resume.parsed_education:
        recommendations.append(Recommendation(
            ats_score=ats_score, recommendation_type="education_gap",
            message=f"Required education ({job.required_education}) could not be confirmed from the resume.",
            priority="medium",
        ))

    final_score = score_result["final_score"]
    if final_score >= 85:
        recommendations.append(Recommendation(
            ats_score=ats_score, recommendation_type="improvement_tip",
            message="Strong overall match — consider prioritizing for an interview.",
            priority="low",
        ))
    elif final_score < 40:
        recommendations.append(Recommendation(
            ats_score=ats_score, recommendation_type="improvement_tip",
            message="Low overall match across semantic, skill, and experience signals — likely not a fit for this role.",
            priority="high",
        ))

    db.add_all(recommendations)


def run_screening(db: Session, resume_id: int, job_id: int) -> ATSScore:
    """Runs (or re-runs) ATS scoring for one resume against one job."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found.")

    existing = (
        db.query(ATSScore)
        .filter(ATSScore.resume_id == resume_id, ATSScore.job_description_id == job_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.flush()

    try:
        score_result = scoring_service.calculate_ats_score(db, resume, job)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    ats_score = ATSScore(
        resume_id=resume.id,
        job_description_id=job.id,
        semantic_score=score_result["semantic_score"],
        skill_match_score=score_result["skill_match_score"],
        experience_match_score=score_result["experience_match_score"],
        final_score=score_result["final_score"],
        status="pending",
    )
    db.add(ats_score)
    db.flush()  # assigns ats_score.id before recommendations reference it

    _generate_recommendations(db, ats_score, score_result, job, resume)

    db.commit()
    db.refresh(ats_score)

    logger.info(
        "Screening complete: resume=%s job=%s final_score=%.2f",
        resume.id, job.id, ats_score.final_score,
    )
    return ats_score


def run_bulk_screening(db: Session, job_id: int) -> List[ATSScore]:
    """
    Runs screening for every uploaded resume against one job. Continues
    past individual failures (e.g. a resume with no extractable text)
    rather than aborting the whole batch, logging each failure.
    """
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found.")

    resumes = db.query(Resume).all()
    results = []
    for resume in resumes:
        try:
            results.append(run_screening(db, resume.id, job.id))
        except HTTPException:
            raise
        except Exception:
            logger.exception("Bulk screening failed for resume %s against job %s", resume.id, job.id)
            continue

    return sorted(results, key=lambda s: s.final_score, reverse=True)


def get_ranked_results(db: Session, job_id: int) -> List[ATSScore]:
    """
    Module 8 — Resume Ranking. Existing ATSScore rows for a job, ranked by
    final_score desc. skill_match_score and experience_match_score break
    ties, in that order, so two candidates with an equal final_score are
    ranked deterministically rather than by insertion order.
    """
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found.")

    return (
        db.query(ATSScore)
        .filter(ATSScore.job_description_id == job_id)
        .order_by(
            ATSScore.final_score.desc(),
            ATSScore.skill_match_score.desc(),
            ATSScore.experience_match_score.desc(),
        )
        .all()
    )


def update_screening_status(db: Session, ats_score_id: int, new_status: str) -> ATSScore:
    ats_score = db.query(ATSScore).filter(ATSScore.id == ats_score_id).first()
    if not ats_score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screening result not found.")
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status value.")
    ats_score.status = new_status
    db.commit()
    db.refresh(ats_score)
    return ats_score


def get_screening_result(db: Session, ats_score_id: int) -> ATSScore:
    ats_score = db.query(ATSScore).filter(ATSScore.id == ats_score_id).first()
    if not ats_score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screening result not found.")
    return ats_score


def build_ats_score_response(ats_score: ATSScore) -> dict:
    """
    Assembles the full API response dict for one ATSScore, including the
    matched/missing/extra skill lists — recomputed here from the resume's
    and job's current skill relationships rather than stored redundantly,
    so they always reflect current data even if skills change after
    scoring ran.
    """
    from app.schemas.screening_schemas import ATSScoreResponse

    skill_result = scoring_service.calculate_skill_match(
        ats_score.resume.skills, ats_score.job_description.skills
    )
    data = ATSScoreResponse.model_validate(ats_score).model_dump(mode="json")
    data["matched_skills"] = skill_result["matched_skills"]
    data["missing_skills"] = skill_result["missing_skills"]
    data["extra_skills"] = skill_result["extra_skills"]
    return data


def build_results_list_item(ats_score: ATSScore) -> dict:
    """
    Flat shape for the /screening/results/all listing — matches what
    frontend/js/results.js's renderResults() actually consumes
    ({id, name, email, score, breakdown, matched, missing, status}),
    which is a different (flatter) contract than build_ats_score_response
    above. Kept as a separate function rather than overloading the fuller
    response, since the two callers have genuinely different shapes.
    """
    skill_result = scoring_service.calculate_skill_match(
        ats_score.resume.skills, ats_score.job_description.skills
    )
    return {
        "id": ats_score.id,
        "name": ats_score.resume.candidate.name,
        "email": ats_score.resume.candidate.email,
        "score": ats_score.final_score,
        "breakdown": {
            "semantic": ats_score.semantic_score,
            "skills": ats_score.skill_match_score,
            "experience": ats_score.experience_match_score,
        },
        "matched": skill_result["matched_skills"],
        "missing": skill_result["missing_skills"],
        "status": ats_score.status,
    }
