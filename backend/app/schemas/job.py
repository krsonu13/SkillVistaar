from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobSkillRequirementCreate(BaseModel):
    skill_id: UUID
    proficiency_level: str = "INTERMEDIATE"
    is_required: bool = True
    minimum_years: float = Field(default=0.0, ge=0)


class JobSkillRequirementResponse(JobSkillRequirementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class ScreeningQuestionCreate(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    question_type: str = "TEXT"
    options: list[str] | None = None
    is_required: bool = True
    display_order: int = 0


class ScreeningQuestionResponse(ScreeningQuestionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    role_family: str | None = Field(default=None, max_length=150)
    occupation_code: str | None = Field(default=None, max_length=100)

    description: str = Field(min_length=10)
    responsibilities: str | None = None

    qualification: str | None = None

    minimum_experience: float = Field(default=0, ge=0)
    maximum_experience: float | None = Field(default=None, ge=0)

    location: str | None = Field(default=None, max_length=255)
    district: str | None = Field(default=None, max_length=150)
    state: str | None = Field(default=None, max_length=150)

    work_mode: str = "ONSITE"

    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)

    vacancies: int = Field(default=1, ge=1)

    shift: str | None = None
    travel_required: bool = False
    joining_timeline: str | None = None

    application_deadline: datetime | None = None

    skill_requirements: list[JobSkillRequirementCreate] = Field(
        default_factory=list
    )

    screening_questions: list[ScreeningQuestionCreate] = Field(
        default_factory=list
    )


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    role_family: str | None = None
    occupation_code: str | None = None
    description: str | None = None
    responsibilities: str | None = None
    qualification: str | None = None

    minimum_experience: float | None = Field(default=None, ge=0)
    maximum_experience: float | None = Field(default=None, ge=0)

    location: str | None = None
    district: str | None = None
    state: str | None = None

    work_mode: str | None = None

    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)

    vacancies: int | None = Field(default=None, ge=1)

    shift: str | None = None
    travel_required: bool | None = None
    joining_timeline: str | None = None

    application_deadline: datetime | None = None

    skill_requirements: list[JobSkillRequirementCreate] | None = None
    screening_questions: list[ScreeningQuestionCreate] | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    created_by_user_id: UUID

    title: str
    role_family: str | None
    occupation_code: str | None
    description: str
    responsibilities: str | None
    qualification: str | None

    minimum_experience: float
    maximum_experience: float | None

    location: str | None
    district: str | None
    state: str | None

    work_mode: str

    salary_min: int | None
    salary_max: int | None

    vacancies: int
    shift: str | None
    travel_required: bool
    joining_timeline: str | None

    application_deadline: datetime | None

    status: str
    is_public: bool

    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    closed_at: datetime | None

    skill_requirements: list[JobSkillRequirementResponse] = Field(
        default_factory=list
    )

    screening_questions: list[ScreeningQuestionResponse] = Field(
        default_factory=list
    )