from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.emerging_skill_trend import (
    EmergingSkillTrendCreate,
    EmergingSkillTrendListResponse,
    EmergingSkillTrendResponse,
)
from app.services.emerging_skill_service import (
    EmergingSkillNotFoundError,
    EmergingSkillService,
    EmergingSkillServiceError,
    EmergingSkillValidationError,
)

router = APIRouter(
    prefix="/emerging-skills",
    tags=["Emerging Skills"],
)


@router.post(
    "/",
    response_model=EmergingSkillTrendResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_emerging_skill_trend(
    data: EmergingSkillTrendCreate,
    db: AsyncSession = Depends(get_db),
):
    service = EmergingSkillService(db)

    try:
        return await service.create_trend(
            skill_id=data.skill_id,
            government_unit_id=data.government_unit_id,
            source_id=data.source_id,
            demand_count=data.demand_count,
            growth_rate=data.growth_rate,
            trend_direction=data.trend_direction,
            rank=data.rank,
            period_start=data.period_start,
            period_end=data.period_end,
        )

    except EmergingSkillValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except EmergingSkillServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{trend_id}",
    response_model=EmergingSkillTrendResponse,
)
async def get_emerging_skill_trend(
    trend_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = EmergingSkillService(db)

    try:
        return await service.get_trend(trend_id)

    except EmergingSkillNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/",
    response_model=EmergingSkillTrendListResponse,
)
async def list_emerging_skill_trends(
    government_unit_id: UUID | None = Query(default=None),
    skill_id: UUID | None = Query(default=None),
    trend_direction: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = EmergingSkillService(db)

    items = await service.list_trends(
        government_unit_id=government_unit_id,
        skill_id=skill_id,
        trend_direction=trend_direction,
        limit=limit,
        offset=offset,
    )

    return EmergingSkillTrendListResponse(
        items=items,
        total=len(items),
    )