from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.course import (
    CourseCreate,
    CourseListResponse,
    CourseResponse,
    CourseUpdate,
)
from app.services.course_service import (
    CourseAccessDeniedError,
    CourseNotFoundError,
    CourseService,
    CourseServiceError,
    CourseValidationError,
)
from app.core.security import get_current_user

router = APIRouter(
    prefix="/courses",
    tags=["Courses"],
)


@router.get(
    "",
    response_model=CourseListResponse,
)
@router.get(
    "/",
    response_model=CourseListResponse,
    include_in_schema=False,
)
async def list_courses_root(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    limit: int | None = Query(default=None, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    keyword: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_db),
):
    effective_limit = limit or page_size
    query_keyword = search or keyword
    courses, total = await CourseService.list_courses(
        db=db,
        keyword=query_keyword,
        page=page,
        page_size=effective_limit,
    )

    return CourseListResponse(
        items=courses,
        total=total,
        page=page,
        page_size=effective_limit,
        pages=CourseService.calculate_pages(
            total,
            effective_limit,
        ),
    )


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_course_root(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.organization import Organization
    from app.models.institution_profile import InstitutionProfile

    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == current_user.id)
    )
    org = org_res.scalars().first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an associated organization.",
        )
    inst_res = await db.execute(
        select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
    )
    inst_profile = inst_res.scalars().first()
    if not inst_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an associated institution profile.",
        )

    try:
        return await CourseService.create_course(
            db=db,
            current_user=current_user,
            institution_profile_id=inst_profile.id,
            data=data,
        )
    except CourseAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except (CourseValidationError, CourseServiceError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/institutions/{institution_profile_id}",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_course(
    institution_profile_id: uuid.UUID,
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await CourseService.create_course(
            db=db,
            current_user=current_user,
            institution_profile_id=institution_profile_id,
            data=data,
        )

    except CourseAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CourseValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except CourseServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/public",
    response_model=CourseListResponse,
)
async def list_public_courses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    limit: int | None = Query(default=None, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    keyword: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_db),
):
    effective_limit = limit or page_size
    query_keyword = search or keyword
    courses, total = await CourseService.list_courses(
        db=db,
        keyword=query_keyword,
        page=page,
        page_size=effective_limit,
    )

    return CourseListResponse(
        items=courses,
        total=total,
        page=page,
        page_size=effective_limit,
        pages=CourseService.calculate_pages(
            total,
            effective_limit,
        ),
    )


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
)
async def get_course(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await CourseService.get_course_for_user(
            db=db,
            current_user=current_user,
            course_id=course_id,
        )

    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CourseAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{course_id}",
    response_model=CourseResponse,
)
async def update_course(
    course_id: uuid.UUID,
    data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await CourseService.update_course(
            db=db,
            current_user=current_user,
            course_id=course_id,
            data=data,
        )

    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CourseAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CourseValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{course_id}/submit-review",
    response_model=CourseResponse,
)
async def submit_course_for_review(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await CourseService.submit_for_review(
            db=db,
            current_user=current_user,
            course_id=course_id,
        )

    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CourseAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CourseValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{course_id}/publish",
    response_model=CourseResponse,
)
async def publish_course(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await CourseService.publish_course(
            db=db,
            current_user=current_user,
            course_id=course_id,
        )

    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CourseAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CourseValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{course_id}/close",
    response_model=CourseResponse,
)
async def close_course(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await CourseService.close_course(
            db=db,
            current_user=current_user,
            course_id=course_id,
        )

    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CourseAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CourseValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{course_id}/archive",
    response_model=CourseResponse,
)
async def archive_course(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await CourseService.archive_course(
            db=db,
            current_user=current_user,
            course_id=course_id,
        )

    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except CourseAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except CourseValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=CourseListResponse,
)
async def list_courses(
    institution_profile_id: uuid.UUID | None = Query(
        default=None,
    ),
    keyword: str | None = Query(
        default=None,
        max_length=255,
    ),
    delivery_mode: str | None = Query(
        default=None,
    ),
    course_level: str | None = Query(
        default=None,
    ),
    city: str | None = Query(
        default=None,
    ),
    state: str | None = Query(
        default=None,
    ),
    admission_open: bool = Query(
        default=False,
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: AsyncSession = Depends(get_db),
):
    courses, total = await CourseService.list_courses(
        db=db,
        institution_profile_id=institution_profile_id,
        keyword=keyword,
        delivery_mode=delivery_mode,
        course_level=course_level,
        city=city,
        state=state,
        admission_open=admission_open,
        page=page,
        page_size=page_size,
    )

    return CourseListResponse(
        items=courses,
        total=total,
        page=page,
        page_size=page_size,
        pages=CourseService.calculate_pages(
            total,
            page_size,
        ),
    )