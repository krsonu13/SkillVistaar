from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.course_alignment import (
    CourseAlignmentCreate,
    CourseAlignmentListResponse,
    CourseAlignmentResponse,
)
from app.services.course_alignment_service import (
    CourseAlignmentNotFoundError,
    CourseAlignmentService,
    CourseAlignmentServiceError,
    CourseAlignmentValidationError,
)

router = APIRouter(
    prefix="/course-alignments",
    tags=["Course Alignment"],
)


@router.post(
    "/",
    response_model=CourseAlignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_course_alignment(
    data: CourseAlignmentCreate,
    db: AsyncSession = Depends(get_db),
):
    service = CourseAlignmentService(db)

    try:
        return await service.create_alignment(
            course_id=data.course_id,
            skill_id=data.skill_id,
            government_unit_id=data.government_unit_id,
            demand_score=data.demand_score,
            skill_coverage_score=data.skill_coverage_score,
            alignment_score=data.alignment_score,
            alignment_status=data.alignment_status,
            recommended_action=data.recommended_action,
        )

    except CourseAlignmentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except CourseAlignmentServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{alignment_id}",
    response_model=CourseAlignmentResponse,
)
async def get_course_alignment(
    alignment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CourseAlignmentService(db)

    try:
        return await service.get_alignment(alignment_id)

    except CourseAlignmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/",
    response_model=CourseAlignmentListResponse,
)
async def list_course_alignments(
    course_id: UUID | None = Query(default=None),
    skill_id: UUID | None = Query(default=None),
    government_unit_id: UUID | None = Query(default=None),
    alignment_status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = CourseAlignmentService(db)

    items = await service.list_alignments(
        course_id=course_id,
        skill_id=skill_id,
        government_unit_id=government_unit_id,
        alignment_status=alignment_status,
        limit=limit,
        offset=offset,
    )

    return CourseAlignmentListResponse(
        items=items,
        total=len(items),
    )