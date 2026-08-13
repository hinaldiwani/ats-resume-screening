"""
app/services/resume_service.py

Orchestrates the full resume upload pipeline:
  1. Validate + save the uploaded file (app/utils/file_handler.py)
  2. Parse it into structured fields (app/services/resume_parser_service.py)
  3. Resolve the Candidate record (app/services/candidate_service.py)
  4. Resolve/link Skill rows (app/services/skill_service.py)
  5. Persist a Resume row

Also provides read operations (get_resume, list_resumes_by_candidate,
list_resumes) used by the resume endpoints and, later, dashboard/search.
"""

import os
import json
import logging
from typing import Optional, List

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Resume
from app.utils.file_handler import validate_upload, save_upload_file
from app.services.resume_parser_service import parse_resume
from app.services.candidate_service import get_or_create_candidate
from app.services.skill_service import get_or_create_skills

logger = logging.getLogger(__name__)


def upload_resume(
    db: Session,
    file: UploadFile,
    candidate_name: Optional[str] = None,
    candidate_email: Optional[str] = None,
) -> Resume:
    """
    Full upload pipeline. `candidate_name`/`candidate_email` are what the
    recruiter typed in the upload form (both optional) — if either is
    missing, the corresponding value parsed from the resume text is used
    instead. If neither source provides an email, candidate_service raises
    a 400, since there's nothing to link the resume to.

    If parsing fails after the file was already saved to disk, the saved
    file is removed so a bad upload doesn't leave an orphaned file behind.
    """
    ext = validate_upload(file)  # raises 400 for unsupported extensions
    file_type = ext.lstrip(".")  # ".pdf" -> "pdf"
    file_path = save_upload_file(file, ext)  # raises 413 if oversized

    try:
        parsed = parse_resume(file_path, file_type)
    except Exception:
        logger.exception("Resume parsing failed for %s; removing saved file", file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to read this file. It may be corrupted or password-protected.",
        )

    final_name = candidate_name or parsed["name"]
    final_email = candidate_email or parsed["email"]

    candidate = get_or_create_candidate(
        db,
        name=final_name,
        email=final_email,
        phone=parsed["phone"],
    )

    skills = get_or_create_skills(db, parsed["skills"])

    resume = Resume(
        candidate_id=candidate.id,
        file_path=file_path,
        file_type=file_type,
        raw_text=parsed["raw_text"],
        parsed_name=parsed["name"],
        parsed_experience_years=parsed["experience_years"],
        parsed_education=parsed["education"],
        parsed_certifications=json.dumps(parsed["certifications"]),
        parsed_projects=json.dumps(parsed["projects"]),
        skills=skills,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    logger.info(
        "Resume uploaded: id=%s candidate_id=%s skills=%d file=%s",
        resume.id, candidate.id, len(skills), file_path,
    )
    return resume


def get_resume(db: Session, resume_id: int) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    return resume


def list_resumes_by_candidate(db: Session, candidate_id: int) -> List[Resume]:
    return (
        db.query(Resume)
        .filter(Resume.candidate_id == candidate_id)
        .order_by(Resume.uploaded_at.desc(), Resume.id.desc())
        .all()
    )


def list_resumes(db: Session, skip: int = 0, limit: int = 50) -> List[Resume]:
    return (
        db.query(Resume)
        .order_by(Resume.uploaded_at.desc(), Resume.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
