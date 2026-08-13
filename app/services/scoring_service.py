"""
app/services/scoring_service.py

Module 7 — ATS Scoring. Computes the full match result between a Resume
and a JobDescription:
  - Cosine similarity between their embeddings (semantic match)
  - Skill match percentage, missing skills, extra skills
  - Experience match (years found vs years required)
  - A single weighted ATS Score from 0-100

All three sub-scores are expressed on a 0-100 scale for consistency and
human-readability, then combined via the SCORE_WEIGHTS below into the
final score. This keeps the ATSScore row auditable — a recruiter (or the
Recommendation entries built from it) can see exactly which signal drove
a given result, per the explainability principle in the architecture doc.
"""

import json
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.models import Resume, JobDescription, Skill
from app.ai.embedding_model import generate_embedding, cosine_similarity

logger = logging.getLogger(__name__)

# Weights sum to 1.0 so the final score stays on a 0-100 scale without
# extra normalization. Tunable here in one place; a future improvement
# (see architecture doc, §13) could make these configurable per job/role
# type rather than a single global default.
SEMANTIC_WEIGHT = 0.4
SKILL_WEIGHT = 0.4
EXPERIENCE_WEIGHT = 0.2


def _get_or_generate_resume_embedding(db: Session, resume: Resume) -> List[float]:
    """Reuses a stored embedding if present; otherwise generates and caches one."""
    if resume.embedding_vector:
        return json.loads(resume.embedding_vector)

    if not resume.raw_text or not resume.raw_text.strip():
        raise ValueError(f"Resume {resume.id} has no extracted text to embed.")

    vector = generate_embedding(resume.raw_text)
    resume.embedding_vector = json.dumps(vector)
    db.commit()
    return vector


def _get_or_generate_job_embedding(db: Session, job: JobDescription) -> List[float]:
    """Reuses a stored embedding if present; otherwise generates and caches one."""
    if job.embedding_vector:
        return json.loads(job.embedding_vector)

    if not job.description or not job.description.strip():
        raise ValueError(f"Job {job.id} has no description text to embed.")

    vector = generate_embedding(job.description)
    job.embedding_vector = json.dumps(vector)
    db.commit()
    return vector


def calculate_skill_match(resume_skills: List[Skill], required_skills: List[Skill]) -> dict:
    """
    Compares skills by id, not name string. Both lists are drawn from the
    shared Skill master table via skill_service's get-or-create, so the
    same real-world skill always has the same id — far more reliable than
    comparing name strings, which could differ in casing or whitespace
    even after normalization elsewhere.

    An empty required-skills list is treated as a 100% match (nothing was
    required, so nothing can be missing) rather than a division-by-zero
    or a 0% score.
    """
    resume_by_id = {s.id: s for s in resume_skills}
    required_by_id = {s.id: s for s in required_skills}

    matched_ids = set(resume_by_id) & set(required_by_id)
    missing_ids = set(required_by_id) - set(resume_by_id)
    extra_ids = set(resume_by_id) - set(required_by_id)

    skill_match_percentage = (
        round(len(matched_ids) / len(required_by_id) * 100, 2) if required_by_id else 100.0
    )

    return {
        "matched_skills": sorted(required_by_id[i].name for i in matched_ids),
        "missing_skills": sorted(required_by_id[i].name for i in missing_ids),
        "extra_skills": sorted(resume_by_id[i].name for i in extra_ids),
        "skill_match_percentage": skill_match_percentage,
    }


def calculate_experience_match(candidate_years: Optional[float], required_years: Optional[float]) -> float:
    """
    0-100 score for how well the candidate's experience aligns with the
    role's requirement.
      - No requirement set                  -> 100 (nothing to fall short of)
      - Requirement set, candidate's years
        weren't found in the resume         -> 50 (neutral: neither penalized
                                                nor rewarded for missing data)
      - Meets or exceeds the requirement     -> 100
      - Below the requirement                -> scaled proportionally, e.g.
                                                2.5 years against a 5-year
                                                requirement -> 50, not a
                                                hard 0 (partial credit)
    """
    if not required_years or required_years <= 0:
        return 100.0
    if candidate_years is None:
        return 50.0
    if candidate_years >= required_years:
        return 100.0
    return round((candidate_years / required_years) * 100, 2)


def calculate_final_score(
    semantic_score_pct: float, skill_match_percentage: float, experience_match_score: float
) -> float:
    """Weighted combination of the three sub-scores, clamped to [0, 100] as a defensive guard."""
    final = (
        semantic_score_pct * SEMANTIC_WEIGHT
        + skill_match_percentage * SKILL_WEIGHT
        + experience_match_score * EXPERIENCE_WEIGHT
    )
    return round(min(100.0, max(0.0, final)), 2)


def calculate_ats_score(db: Session, resume: Resume, job: JobDescription) -> dict:
    """
    Full scoring pipeline for one resume against one job description.
    Returns every sub-score plus the final weighted score and the
    matched/missing/extra skill lists — everything needed to populate an
    ATSScore row and its explanatory Recommendation entries.
    """
    resume_vector = _get_or_generate_resume_embedding(db, resume)
    job_vector = _get_or_generate_job_embedding(db, job)

    semantic_similarity = cosine_similarity(resume_vector, job_vector)  # 0-1
    semantic_score_pct = round(semantic_similarity * 100, 2)  # 0-100

    skill_result = calculate_skill_match(resume.skills, job.skills)
    experience_score = calculate_experience_match(resume.parsed_experience_years, job.min_experience_years)

    final_score = calculate_final_score(
        semantic_score_pct, skill_result["skill_match_percentage"], experience_score
    )

    result = {
        "semantic_score": semantic_score_pct,
        "skill_match_score": skill_result["skill_match_percentage"],
        "experience_match_score": experience_score,
        "final_score": final_score,
        "matched_skills": skill_result["matched_skills"],
        "missing_skills": skill_result["missing_skills"],
        "extra_skills": skill_result["extra_skills"],
    }

    logger.info(
        "Scored resume %s against job %s: final=%.2f (semantic=%.2f, skills=%.2f, experience=%.2f)",
        resume.id, job.id, final_score, semantic_score_pct,
        skill_result["skill_match_percentage"], experience_score,
    )
    return result
