"""
app/api/v1/endpoints/dashboard.py

Dashboard routes. Paths match the existing frontend's calls exactly
(frontend/js/dashboard.js), since that code is fixed and not modified as
part of this backend build:
  - GET /dashboard/stats             (frontend calls this exact path)
  - GET /dashboard/top-candidates/all (literal "all", not job-scoped —
                                        matches the frontend's fetch call)
  - GET /dashboard/recent-uploads     (not yet called by the frontend,
                                        but included per the module spec;
                                        available for a future page)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth_dependency import get_current_recruiter
from app.models.models import Recruiter
from app.schemas.schemas import APIResponse
from app.services import dashboard_service

router = APIRouter()


@router.get("/stats", response_model=APIResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    stats = dashboard_service.get_dashboard_stats(db, current_recruiter.id)
    return APIResponse(success=True, data=stats, message="Dashboard stats retrieved.")


@router.get("/top-candidates/all", response_model=APIResponse)
@router.get("/top-candidates", response_model=APIResponse)
def get_top_candidates(

    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    candidates = dashboard_service.get_top_candidates(db, current_recruiter.id, limit=limit)
    return APIResponse(success=True, data=candidates, message=f"{len(candidates)} top candidate(s).")


@router.get("/recent-uploads", response_model=APIResponse)
def get_recent_uploads(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_recruiter: Recruiter = Depends(get_current_recruiter),
):
    uploads = dashboard_service.get_recent_uploads(db, limit=limit)
    return APIResponse(success=True, data=uploads, message=f"{len(uploads)} recent upload(s).")
