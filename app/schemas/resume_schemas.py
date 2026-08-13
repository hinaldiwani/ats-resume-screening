"""
app/schemas/resume_schemas.py
"""

import json
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.skill_schemas import SkillResponse
from app.schemas.candidate_schemas import CandidateResponse


class ResumeResponse(BaseModel):
    id: int
    candidate_id: int
    file_type: str
    parsed_name: Optional[str] = None
    parsed_experience_years: Optional[float] = None
    parsed_education: Optional[str] = None
    parsed_certifications: List[str] = []
    parsed_projects: List[str] = []
    uploaded_at: datetime
    skills: List[SkillResponse] = []
    candidate: Optional[CandidateResponse] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("parsed_certifications", "parsed_projects", mode="before")
    @classmethod
    def _parse_json_list(cls, value):
        """The model stores these as JSON-serialized text; deserialize to a
        real list for the API response. Falls back to an empty list for
        None or malformed data rather than raising, since a resume with
        no certifications/projects is a normal case, not an error."""
        if value is None:
            return []
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        return value


class ResumeTextPreview(BaseModel):
    """Separate, smaller schema for when the raw text itself is needed
    (e.g. a future 'view extracted text' feature) without bloating the
    default resume list/detail responses above."""
    id: int
    raw_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
