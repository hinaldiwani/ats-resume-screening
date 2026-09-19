import os
import uuid
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import get_db
from backend.models import Job, Candidate, Resume, ScreeningResult, User
from backend.schemas import ResumeResponse
from backend.services.resume_parser import resume_parser
from backend.services.ats_engine import ats_engine
from backend.services.auth import get_current_user

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@router.get("", response_model=List[ResumeResponse])
def get_resumes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all resumes associated with the current recruiter's jobs."""
    resumes = (
        db.query(Resume)
        .join(Job, Job.id == Resume.job_id)
        .filter(Job.recruiter_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )
    return [ResumeResponse.model_validate(r) for r in resumes]

@router.post("/upload", response_model=List[ResumeResponse])
async def upload_resumes(
    job_id: int = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or access denied")

    uploaded_resumes = []

    req_skills = [s.strip() for s in (job.required_skills_text or "").split(",") if s.strip()]
    pref_skills = [s.strip() for s in (job.preferred_skills_text or "").split(",") if s.strip()]

    for file in files:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".docx", ".doc"]:
            continue

        file_bytes = await file.read()
        if not file_bytes:
            continue

        # Save file to disk
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Extract text & info with resume parser
        parsed = resume_parser.parse(file_bytes, filename)

        # Create candidate or retrieve existing
        cand_email = parsed.get("email") or f"cand_{uuid.uuid4().hex[:8]}@example.com"
        candidate = db.query(Candidate).filter(Candidate.email == cand_email).first()
        if not candidate:
            candidate = Candidate(
                name=parsed.get("name") or "Candidate",
                email=cand_email,
                phone=parsed.get("phone") or "",
                education=parsed.get("education"),
                experience_years=parsed.get("experience_years"),
                raw_resume_text=parsed.get("raw_text") or "",
                links_json=json.dumps(parsed.get("links") or {})
            )
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
        else:
            # Update candidate details with actual detected values
            candidate.raw_resume_text = parsed.get("raw_text") or candidate.raw_resume_text
            if parsed.get("education"):
                candidate.education = parsed.get("education")
            if parsed.get("experience_years") is not None:
                candidate.experience_years = parsed.get("experience_years")
            db.commit()

        # Create Resume record
        resume = Resume(
            candidate_id=candidate.id,
            job_id=job.id,
            filename=filename,
            file_path=file_path,
            file_type=ext.replace(".", ""),
            parsed_text=parsed.get("raw_text") or ""
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)

        # Execute ATS Screening Algorithm
        screen_res = ats_engine.screen(
            resume_text=parsed.get("raw_text") or "",
            cand_name=candidate.name,
            cand_email=candidate.email,
            cand_phone=candidate.phone,
            cand_edu=candidate.education,
            cand_exp_years=candidate.experience_years,
            cand_links=parsed.get("links") or {},
            job_title=job.title,
            job_description=job.description,
            job_req_skills=req_skills,
            job_pref_skills=pref_skills,
            job_min_exp=job.min_experience,
            job_max_exp=job.max_experience,
            job_edu=job.education,
            sections=parsed.get("sections"),
            word_count=parsed.get("word_count")
        )

        # Check existing screening result
        existing_scr = db.query(ScreeningResult).filter(ScreeningResult.resume_id == resume.id).first()
        if existing_scr:
            db.delete(existing_scr)
            db.commit()

        scr = ScreeningResult(
            resume_id=resume.id,
            job_id=job.id,
            candidate_id=candidate.id,
            overall_score=screen_res["overall_score"],
            skills_score=screen_res["skills_score"],
            experience_score=screen_res["experience_score"],
            education_score=screen_res["education_score"],
            keyword_score=screen_res["keyword_score"],
            resume_quality_score=screen_res["resume_quality_score"],
            matched_skills_json=json.dumps(screen_res["matched_skills"]),
            missing_skills_json=json.dumps(screen_res["missing_skills"]),
            status=screen_res["status"],
            recommendation=screen_res["recommendation"],
            feedback_summary=screen_res["explanation"],
            detected_experience=screen_res["detected_experience"],
            detected_education=screen_res["detected_education"],
            job_keywords_json=json.dumps(screen_res["matched_keywords"]),
            explanation=screen_res["explanation"]
        )
        db.add(scr)
        db.commit()

        resp = ResumeResponse.model_validate(resume)
        uploaded_resumes.append(resp)

    return uploaded_resumes
