"""
app/services/skill_service.py

Skill is a shared master table (see architecture doc, §5) — this service
is the single place that resolves a skill name to a Skill row, creating it
if it doesn't exist yet. Every other service (resume upload, job creation)
goes through this rather than inserting Skill rows directly, so dedup logic
lives in exactly one place.
"""

from typing import List
from sqlalchemy.orm import Session

from app.models.models import Skill


def get_or_create_skill(db: Session, name: str) -> Skill:
    """
    Case-insensitive lookup: "python", "Python", and "PYTHON" all resolve
    to the same row, stored with the first-seen casing.
    """
    normalized = name.strip()
    if not normalized:
        return None

    existing = db.query(Skill).filter(Skill.name.ilike(normalized)).first()
    if existing:
        return existing

    skill = Skill(name=normalized)
    db.add(skill)
    db.flush()  # assigns an id without committing, so callers can batch multiple skills in one transaction
    return skill


def get_or_create_skills(db: Session, names: List[str]) -> List[Skill]:
    seen = set()
    skills = []
    for name in names:
        key = name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        skills.append(get_or_create_skill(db, name))
    return skills
