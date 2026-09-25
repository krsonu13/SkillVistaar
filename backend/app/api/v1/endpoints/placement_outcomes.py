from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.placement_outcome import (
    PlacementOutcomeCreate,
    PlacementOutcomeListResponse,
    PlacementOutcomeResponse,
    PlacementOutcomeSummaryResponse,
)
from app.services.placement_outcome_service import (
    PlacementOutcomeNotFoundError,
    PlacementOutcomeService,
    PlacementOutcomeServiceError,
    PlacementOutcomeValidationError,
)

router = APIRouter(
    prefix="/placement-outcomes",
    tags=["Placement Outcomes"],
)


@router.post(
    "/",
    response_model=PlacementOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_placement_outcome(
    data: PlacementOutcomeCreate,
    db: AsyncSession = Depends(get_db),
):
    service = PlacementOutcomeService(db)

    try:
        return await service.create_outcome(
            institution_profile_id=data.institution_profile_id,
            course_id=data.course_id,
            government_unit_id=data.government_unit_id,
            occupation_name=data.occupation_name,
            sector=data.sector,
            total_learners=data.total_learners,
            placed_learners=data.placed_learners,
            employment_rate=data.employment_rate,
            average_salary=data.average_salary,
            median_salary=data.median_salary,
            currency=data.currency,
            period_start=data.period_start,
            period_end=data.period_end,
            source_id=data.source_id,
            notes=data.notes,
        )

    except PlacementOutcomeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except PlacementOutcomeServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{outcome_id}",
    response_model=PlacementOutcomeResponse,
)
async def get_placement_outcome(
    outcome_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = PlacementOutcomeService(db)

    try:
        return await service.get_outcome(outcome_id)

    except PlacementOutcomeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/",
    response_model=PlacementOutcomeListResponse,
)
async def list_placement_outcomes(
    institution_profile_id: UUID | None = Query(default=None),
    course_id: UUID | None = Query(default=None),
    government_unit_id: UUID | None = Query(default=None),
    occupation_name: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = PlacementOutcomeService(db)

    items = await service.list_outcomes(
        institution_profile_id=institution_profile_id,
        course_id=course_id,
        government_unit_id=government_unit_id,
        occupation_name=occupation_name,
        sector=sector,
        limit=limit,
        offset=offset,
    )

    return PlacementOutcomeListResponse(
        items=items,
        total=len(items),
    )


@router.get(
    "/summary/overview",
    response_model=PlacementOutcomeSummaryResponse,
)
async def placement_outcome_summary(
    government_unit_id: UUID | None = Query(default=None),
    course_id: UUID | None = Query(default=None),
    institution_profile_id: UUID | None = Query(default=None),
    sector: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    service = PlacementOutcomeService(db)

    return await service.get_summary(
        government_unit_id=government_unit_id,
        course_id=course_id,
        institution_profile_id=institution_profile_id,
        sector=sector,
    )