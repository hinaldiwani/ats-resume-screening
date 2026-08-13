"""
app/api/v1/api.py

Aggregates all v1 endpoint routers into a single APIRouter, which is then
mounted once in main.py under the configured API_V1_PREFIX.

Endpoint routers themselves (in app/api/v1/endpoints/) currently contain no
routes yet — they are placeholders to be filled in the business-logic phase.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    jobs,
    candidates,
    resumes,
    screening,
    dashboard,
    notifications,
    reports,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["Candidates"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(screening.router, prefix="/screening", tags=["Screening"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
