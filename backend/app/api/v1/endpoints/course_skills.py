from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    get_current_user,
    get_optional_current_user,
)
from app.db.session import get_db
from app.models.user import User
from app.services.course_skill_service import (
    CourseSkillAccessDeniedError,
    CourseSkillNotFoundError,
    CourseSkillService,
    CourseSkillServiceError,
    CourseSkillValidationError,
)


router = APIRouter(
    prefix="/courses",
    tags=["Course Skills"],
)


class CourseSkillCreateRequest(BaseModel):
    skill_id: UUID
    importance: str = Field(
        default="CORE",
        max_length=30,
    )
    proficiency_level: str = Field(
        default="BEGINNER",
        max_length=30,
    )
    is_mandatory: bool = True
    module_name: str | None = Field(
        default=None,
        max_length=255,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )


class CourseSkillUpdateRequest(BaseModel):
    importance: str | None = Field(
        default=None,
        max_length=30,
    )
    proficiency_level: str | None = Field(
        default=None,
        max_length=30,
    )
    is_mandatory: bool | None = None
    module_name: str | None = Field(
        default=None,
        max_length=255,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )


def _handle_service_error(exc: Exception) -> None:
    if isinstance(exc, CourseSkillNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, CourseSkillAccessDeniedError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(exc, CourseSkillValidationError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if isinstance(exc, CourseSkillServiceError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    raise exc


@router.post(
    "/{course_id}/skills",
    status_code=status.HTTP_201_CREATED,
)
async def add_course_skill(
    course_id: UUID,
    payload: CourseSkillCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await CourseSkillService.add_skill(
            db=db,
            course_id=course_id,
            skill_id=payload.skill_id,
            importance=payload.importance,
            proficiency_level=payload.proficiency_level,
            is_mandatory=payload.is_mandatory,
            module_name=payload.module_name,
            description=payload.description,
            current_user=current_user,
        )
    except Exception as exc:
        _handle_service_error(exc)


@router.get(
    "/{course_id}/skills",
)
async def list_course_skills(
    course_id: UUID,
    include_all: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(
        get_optional_current_user
    ),
):
    try:
        return await CourseSkillService.list_course_skills(
            db=db,
            course_id=course_id,
            current_user=current_user,
            include_all=include_all,
        )
    except Exception as exc:
        _handle_service_error(exc)


@router.patch(
    "/skill-mappings/{mapping_id}",
)
async def update_course_skill(
    mapping_id: UUID,
    payload: CourseSkillUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await CourseSkillService.update_skill(
            db=db,
            mapping_id=mapping_id,
            importance=payload.importance,
            proficiency_level=payload.proficiency_level,
            is_mandatory=payload.is_mandatory,
            module_name=payload.module_name,
            description=payload.description,
            current_user=current_user,
        )
    except Exception as exc:
        _handle_service_error(exc)


@router.delete(
    "/skill-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_course_skill(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await CourseSkillService.remove_skill(
            db=db,
            mapping_id=mapping_id,
            current_user=current_user,
        )
    except Exception as exc:
        _handle_service_error(exc)
