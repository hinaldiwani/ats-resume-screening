from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import Job, User, Resume, ScreeningResult, JobSkill, Skill
from backend.schemas import JobCreate, JobUpdate, JobResponse
from backend.services.auth import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.get("", response_model=List[JobResponse])
def get_jobs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    jobs = db.query(Job).filter(Job.recruiter_id == current_user.id).order_by(Job.created_at.desc()).all()
    results = []
    for j in jobs:
        total_resumes = db.query(Resume).filter(Resume.job_id == j.id).count()
        shortlisted = db.query(ScreeningResult).filter(
            ScreeningResult.job_id == j.id,
            ScreeningResult.status == "Shortlisted"
        ).count()

        resp = JobResponse.model_validate(j)
        resp.total_resumes = total_resumes
        resp.shortlisted_count = shortlisted
        results.append(resp)

    return results

@router.post("", response_model=JobResponse)
def create_job(job_data: JobCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req_skills_str = ", ".join(job_data.required_skills) if job_data.required_skills else ""
    pref_skills_str = ", ".join(job_data.preferred_skills) if job_data.preferred_skills else ""

    job = Job(
        recruiter_id=current_user.id,
        title=job_data.title.strip(),
        department=job_data.department or "Engineering",
        description=job_data.description.strip(),
        required_skills_text=req_skills_str,
        preferred_skills_text=pref_skills_str,
        min_experience=job_data.min_experience or 0.0,
        max_experience=job_data.max_experience or 10.0,
        education=job_data.education or "Bachelor's Degree",
        location=job_data.location or "Remote / Hybrid",
        status="Open"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Attach skills to job_skills
    all_skills = (job_data.required_skills or []) + (job_data.preferred_skills or [])
    for skill_name in all_skills:
        s_clean = skill_name.strip()
        if not s_clean:
            continue
        skill_obj = db.query(Skill).filter(Skill.name == s_clean).first()
        if not skill_obj:
            skill_obj = Skill(name=s_clean)
            db.add(skill_obj)
            db.commit()
            db.refresh(skill_obj)

        js = JobSkill(
            job_id=job.id,
            skill_id=skill_obj.id,
            is_required=(skill_name in (job_data.required_skills or [])),
            weight=4 if skill_name in (job_data.required_skills or []) else 2
        )
        db.add(js)

    db.commit()
    resp = JobResponse.model_validate(job)
    resp.total_resumes = 0
    resp.shortlisted_count = 0
    return resp

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    total_resumes = db.query(Resume).filter(Resume.job_id == job.id).count()
    shortlisted = db.query(ScreeningResult).filter(
        ScreeningResult.job_id == job.id,
        ScreeningResult.status == "Shortlisted"
    ).count()

    resp = JobResponse.model_validate(job)
    resp.total_resumes = total_resumes
    resp.shortlisted_count = shortlisted
    return resp


@router.put("/{job_id}", response_model=JobResponse)
def update_job(job_id: int, job_data: JobUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_data.title is not None:
        job.title = job_data.title
    if job_data.department is not None:
        job.department = job_data.department
    if job_data.description is not None:
        job.description = job_data.description
    if job_data.required_skills is not None:
        job.required_skills_text = ", ".join(job_data.required_skills)
    if job_data.preferred_skills is not None:
        job.preferred_skills_text = ", ".join(job_data.preferred_skills)
    if job_data.min_experience is not None:
        job.min_experience = job_data.min_experience
    if job_data.max_experience is not None:
        job.max_experience = job_data.max_experience
    if job_data.education is not None:
        job.education = job_data.education
    if job_data.location is not None:
        job.location = job_data.location
    if job_data.status is not None:
        job.status = job_data.status

    db.commit()
    db.refresh(job)

    total_resumes = db.query(Resume).filter(Resume.job_id == job.id).count()
    shortlisted = db.query(ScreeningResult).filter(
        ScreeningResult.job_id == job.id,
        ScreeningResult.status == "Shortlisted"
    ).count()

    resp = JobResponse.model_validate(job)
    resp.total_resumes = total_resumes
    resp.shortlisted_count = shortlisted
    return resp

@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()
    return {"message": "Job deleted successfully"}
