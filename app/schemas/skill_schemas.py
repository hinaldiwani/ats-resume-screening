"""app/schemas/skill_schemas.py"""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SkillResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
