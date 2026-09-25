from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.labour_market import (
    LabourMarketSnapshotCreate,
    LabourMarketSnapshotListResponse,
    LabourMarketSnapshotResponse,
    LabourMarketSourceCreate,
    LabourMarketSourceResponse,
    LabourMarketSummaryResponse,
)
from app.services.labour_market_service import (
    LabourMarketNotFoundError,
    LabourMarketService,
    LabourMarketServiceError,
    LabourMarketValidationError,
)

router = APIRouter(
    prefix="/labour-market",
    tags=["Labour Market Intelligence"],
)


@router.post(
    "/sources",
    response_model=LabourMarketSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    data: LabourMarketSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a labour-market data source.

    Authorization will be enforced through the government/admin
    permission layer as the administration module is connected.
    """
    service = LabourMarketService(db)

    try:
        source = await service.create_source(
            name=data.name,
            source_type=data.source_type,
            organization_name=data.organization_name,
            description=data.description,
            source_url=data.source_url,
            collection_method=data.collection_method,
            reliability_score=data.reliability_score,
        )
        return source

    except LabourMarketValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except LabourMarketServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/sources/{source_id}",
    response_model=LabourMarketSourceResponse,
)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = LabourMarketService(db)

    try:
        return await service.get_source(source_id)

    except LabourMarketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/snapshots",
    response_model=LabourMarketSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_snapshot(
    data: LabourMarketSnapshotCreate,
    db: AsyncSession = Depends(get_db),
):
    service = LabourMarketService(db)

    try:
        return await service.create_snapshot(
            government_unit_id=data.government_unit_id,
            source_id=data.source_id,
            skill_id=data.skill_id,
            occupation_code=data.occupation_code,
            occupation_name=data.occupation_name,
            sector=data.sector,
            employment_type=data.employment_type,
            workplace_type=data.workplace_type,
            experience_min=data.experience_min,
            experience_max=data.experience_max,
            demand_count=data.demand_count,
            supply_count=data.supply_count,
            average_salary=data.average_salary,
            median_salary=data.median_salary,
            currency=data.currency,
            period_start=data.period_start,
            period_end=data.period_end,
            notes=data.notes,
        )

    except LabourMarketValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except LabourMarketServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/snapshots",
    response_model=LabourMarketSnapshotListResponse,
)
async def list_snapshots(
    government_unit_id: UUID | None = Query(default=None),
    skill_id: UUID | None = Query(default=None),
    occupation_name: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = LabourMarketService(db)

    items = await service.list_snapshots(
        government_unit_id=government_unit_id,
        skill_id=skill_id,
        occupation_name=occupation_name,
        sector=sector,
        limit=limit,
        offset=offset,
    )

    return LabourMarketSnapshotListResponse(
        items=items,
        total=len(items),
    )


@router.get(
    "/summary",
    response_model=LabourMarketSummaryResponse,
)
async def demand_supply_summary(
    government_unit_id: UUID | None = Query(default=None),
    skill_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    service = LabourMarketService(db)

    summary = await service.get_demand_supply_summary(
        government_unit_id=government_unit_id,
        skill_id=skill_id,
    )

    return summary

@router.get(
    "/sources",
    response_model=list[LabourMarketSourceResponse],
)
async def list_sources(
    source_type: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = LabourMarketService(db)

    return await service.list_sources(
        source_type=source_type,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=LabourMarketSnapshotResponse,
)
async def get_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = LabourMarketService(db)

    try:
        return await service.get_snapshot(snapshot_id)

    except LabourMarketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc