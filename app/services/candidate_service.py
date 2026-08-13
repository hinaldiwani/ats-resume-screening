"""
app/services/candidate_service.py

Business logic for candidates. Routes call these functions rather than
touching the DB directly, matching the pattern established in
auth_service.py.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import Candidate
from app.schemas.candidate_schemas import CandidateCreateRequest

logger = logging.getLogger(__name__)


def create_candidate(db: Session, payload: CandidateCreateRequest) -> Candidate:
    """Creates a new candidate. Raises 409 if the email is already registered."""
    existing = db.query(Candidate).filter(Candidate.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A candidate with this email already exists.",
        )

    candidate = Candidate(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        location=payload.location,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    logger.info("Created candidate id=%s email=%s", candidate.id, candidate.email)
    return candidate


def get_or_create_candidate(
    db: Session,
    name: Optional[str],
    email: Optional[str],
    phone: Optional[str] = None,
) -> Candidate:
    """
    Used by the resume upload flow: if a candidate with this email already
    exists, reuse it (filling in name/phone only if they were previously
    blank); otherwise create a new one. Falls back to a placeholder name
    derived from the email if no name is supplied at all, since Candidate.name
    is a required column.

    Raises 400 if no email is available to key off of — an anonymous resume
    upload with neither a supplied email nor one extracted by the parser
    can't be linked to a candidate record.
    """
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidate email available — provide one, or ensure the resume text contains one.",
        )

    existing = db.query(Candidate).filter(Candidate.email == email).first()
    if existing:
        if not existing.name and name:
            existing.name = name
        if not existing.phone and phone:
            existing.phone = phone
        db.commit()
        db.refresh(existing)
        return existing

    candidate = Candidate(
        name=name or email.split("@")[0],
        email=email,
        phone=phone,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    logger.info("Auto-created candidate id=%s email=%s via resume upload", candidate.id, candidate.email)
    return candidate


def get_candidate(db: Session, candidate_id: int) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return candidate


def list_candidates(db: Session, skip: int = 0, limit: int = 50) -> List[Candidate]:
    """
    Ordered by created_at desc, id desc. The id tiebreaker matters because
    DATETIME has only second-level resolution in both SQLite and MySQL's
    default column type — candidates created within the same second would
    otherwise sort in an undefined order.
    """
    return (
        db.query(Candidate)
        .order_by(Candidate.created_at.desc(), Candidate.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
