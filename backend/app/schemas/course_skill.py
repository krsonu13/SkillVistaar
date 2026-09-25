from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CourseSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    skill_id: uuid.UUID

    importance: str
    proficiency_level: str
    is_mandatory: bool

    module_name: str | None = None
    description: str | None = None

    created_at: datetime
    updated_at: datetime


class CourseSkillListResponse(BaseModel):
    items: list[CourseSkillResponse]
    total: int