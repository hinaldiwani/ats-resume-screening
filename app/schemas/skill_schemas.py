"""
app/schemas/skill_schemas.py

Schema for the Skill entity, nested inside Resume and JobDescription responses.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class SkillResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
