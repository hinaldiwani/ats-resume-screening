"""
app/models/__init__.py

Re-exports all models so they can be imported as `from app.models import Recruiter`
etc., in addition to `from app.models.models import Recruiter`.
"""

from app.models.models import (  # noqa: F401
    Recruiter,
    Candidate,
    Resume,
    JobDescription,
    Skill,
    ATSScore,
    Recommendation,
    resume_skills,
    job_skills,
)
from app.models.token_blacklist import TokenBlacklist  # noqa: F401
