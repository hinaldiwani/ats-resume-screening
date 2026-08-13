"""
app/api/v1/endpoints/reports.py

Report download routes — PDF and Excel exports of a job's ranked
screening results. Read access follows the same convention as job/results
reads elsewhere: open to any authenticated recruiter.
"""

import io
import re

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth_dependency import get_current_recruiter
from app.models.models import Recruiter
from app.services import job_service, screening_service, report_service

router = APIRouter()


def _safe_filename(title: str) -> str:
    """Sanitizes a job title into a safe filename fragment (letters, numbers, hyphens only)."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    return slug or "job"


@router.get("/job/{job_id}/pdf")
def download_pdf_report(
    job_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    job = job_service.get_job(db, job_id)
    ats_scores = screening_service.get_ranked_results(db, job_id)
    pdf_bytes = report_service.generate_pdf_report(job, ats_scores)
    filename = f"ats-report-{_safe_filename(job.title)}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/job/{job_id}/excel")
def download_excel_report(
    job_id: int,
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    job = job_service.get_job(db, job_id)
    ats_scores = screening_service.get_ranked_results(db, job_id)
    excel_bytes = report_service.generate_excel_report(job, ats_scores)
    filename = f"ats-report-{_safe_filename(job.title)}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
