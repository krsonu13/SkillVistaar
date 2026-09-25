from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.government_analytics_service import (
    GovernmentAnalyticsService,
)
from app.schemas.government_analytics import (
    CourseAlignmentOverview,
    DemandSupplyOverview,
    EmergingSkillItem,
    GovernmentDashboardResponse,
    OccupationDemandItem,
    PlacementOverview,
)

router = APIRouter(
    prefix="/government/analytics",
    tags=["Government Analytics"],
)


@router.get("/dashboard", response_model=GovernmentDashboardResponse)
async def government_dashboard(
    government_unit_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregated government labour-market intelligence dashboard.

    The response intentionally contains aggregated intelligence
    rather than individual candidate PII.
    """
    service = GovernmentAnalyticsService(db)

    return await service.dashboard(
        government_unit_id=government_unit_id,
    )


@router.get("/demand", response_model=DemandSupplyOverview)
async def government_demand_overview(
    government_unit_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    service = GovernmentAnalyticsService(db)

    return await service.demand_overview(
        government_unit_id=government_unit_id,
    )


@router.get("/occupations", response_model=list[OccupationDemandItem])
async def government_top_occupations(
    government_unit_id: UUID | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = GovernmentAnalyticsService(db)

    return await service.top_occupations(
        government_unit_id=government_unit_id,
        limit=limit,
    )


@router.get("/emerging-skills", response_model=list[EmergingSkillItem])
async def government_emerging_skills(
    government_unit_id: UUID | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = GovernmentAnalyticsService(db)

    return await service.emerging_skills(
        government_unit_id=government_unit_id,
        limit=limit,
    )


@router.get("/placements", response_model=PlacementOverview)
async def government_placement_overview(
    government_unit_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    service = GovernmentAnalyticsService(db)

    return await service.placement_overview(
        government_unit_id=government_unit_id,
    )


@router.get("/course-alignment", response_model=CourseAlignmentOverview)
async def government_course_alignment(
    government_unit_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    service = GovernmentAnalyticsService(db)

    return await service.course_alignment_overview(
        government_unit_id=government_unit_id,
    )