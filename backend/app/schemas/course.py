from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CourseCreate(BaseModel):
    course_code: str | None = Field(
        default=None,
        max_length=100,
    )

    title: str = Field(
        min_length=2,
        max_length=255,
    )

    short_description: str | None = Field(
        default=None,
        max_length=1000,
    )

    description: str | None = None

    course_level: str = Field(
        default="BEGINNER",
        max_length=30,
    )

    delivery_mode: str = Field(
        default="OFFLINE",
        max_length=30,
    )

    duration_value: int = Field(
        default=1,
        ge=1,
        le=120,
    )

    duration_unit: str = Field(
        default="MONTHS",
        max_length=30,
    )

    fee: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
        max_digits=12,
    )

    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=10,
    )

    eligibility: str | None = None

    seats: int | None = Field(
        default=None,
        ge=1,
        le=100000,
    )

    batch_start_date: date | None = None
    batch_end_date: date | None = None

    admission_start_date: date | None = None
    admission_end_date: date | None = None

    syllabus: str | None = None

    placement_support: bool = False

    placement_rate: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        decimal_places=2,
        max_digits=5,
    )

    is_featured: bool = False

    @field_validator(
        "course_level",
        "delivery_mode",
        "duration_unit",
        "currency",
        mode="before",
    )
    @classmethod
    def normalize_uppercase(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Course title cannot be empty.")

        return value

    @field_validator("course_code")
    @classmethod
    def normalize_course_code(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip().upper()

        return value or None

    @field_validator("batch_end_date")
    @classmethod
    def validate_batch_dates(
        cls,
        value: date | None,
    ) -> date | None:
        return value

    @field_validator("admission_end_date")
    @classmethod
    def validate_admission_dates(
        cls,
        value: date | None,
    ) -> date | None:
        return value


class CourseUpdate(BaseModel):
    course_code: str | None = Field(
        default=None,
        max_length=100,
    )

    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    short_description: str | None = Field(
        default=None,
        max_length=1000,
    )

    description: str | None = None

    course_level: str | None = Field(
        default=None,
        max_length=30,
    )

    delivery_mode: str | None = Field(
        default=None,
        max_length=30,
    )

    duration_value: int | None = Field(
        default=None,
        ge=1,
        le=120,
    )

    duration_unit: str | None = Field(
        default=None,
        max_length=30,
    )

    fee: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
        max_digits=12,
    )

    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=10,
    )

    eligibility: str | None = None

    seats: int | None = Field(
        default=None,
        ge=1,
        le=100000,
    )

    batch_start_date: date | None = None
    batch_end_date: date | None = None

    admission_start_date: date | None = None
    admission_end_date: date | None = None

    syllabus: str | None = None

    placement_support: bool | None = None

    placement_rate: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        decimal_places=2,
        max_digits=5,
    )

    is_featured: bool | None = None

    @field_validator(
        "course_level",
        "delivery_mode",
        "duration_unit",
        "currency",
        mode="before",
    )
    @classmethod
    def normalize_uppercase(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Course title cannot be empty.")

        return value

    @field_validator("course_code")
    @classmethod
    def normalize_course_code(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip().upper()

        return value or None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution_profile_id: uuid.UUID

    course_code: str | None

    title: str
    short_description: str | None
    description: str | None

    course_level: str
    delivery_mode: str

    duration_value: int
    duration_unit: str

    fee: Decimal | None
    currency: str

    eligibility: str | None
    seats: int | None

    batch_start_date: date | None
    batch_end_date: date | None

    admission_start_date: date | None
    admission_end_date: date | None

    syllabus: str | None

    placement_support: bool
    placement_rate: Decimal | None

    status: str
    is_featured: bool

    published_at: datetime | None
    closed_at: datetime | None

    created_at: datetime
    updated_at: datetime


class CourseListResponse(BaseModel):
    items: list[CourseResponse]
    total: int
    page: int
    page_size: int
    pages: int