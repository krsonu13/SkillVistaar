from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emerging_skill_trend import EmergingSkillTrend
from app.models.government_unit import GovernmentUnit
from app.models.labour_market_source import LabourMarketSource
from app.models.skill import Skill


class EmergingSkillServiceError(Exception):
    pass


class EmergingSkillValidationError(EmergingSkillServiceError):
    pass


class EmergingSkillNotFoundError(EmergingSkillServiceError):
    pass


class EmergingSkillService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_trend(
        self,
        trend_id: UUID,
    ) -> EmergingSkillTrend:
        result = await self.db.execute(
            select(EmergingSkillTrend).where(
                EmergingSkillTrend.id == trend_id
            )
        )

        trend = result.scalar_one_or_none()

        if trend is None:
            raise EmergingSkillNotFoundError(
                f"Emerging skill trend {trend_id} not found."
            )

        return trend

    async def validate_skill(
        self,
        skill_id: UUID,
    ) -> Skill:
        result = await self.db.execute(
            select(Skill).where(Skill.id == skill_id)
        )

        skill = result.scalar_one_or_none()

        if skill is None:
            raise EmergingSkillValidationError(
                "Skill does not exist."
            )

        if not skill.is_active:
            raise EmergingSkillValidationError(
                "Skill is inactive."
            )

        return skill

    async def validate_unit(
        self,
        government_unit_id: UUID | None,
    ) -> GovernmentUnit | None:
        if government_unit_id is None:
            return None

        result = await self.db.execute(
            select(GovernmentUnit).where(
                GovernmentUnit.id == government_unit_id
            )
        )

        unit = result.scalar_one_or_none()

        if unit is None:
            raise EmergingSkillValidationError(
                "Government unit does not exist."
            )

        if not unit.is_active:
            raise EmergingSkillValidationError(
                "Government unit is inactive."
            )

        return unit

    async def validate_source(
        self,
        source_id: UUID | None,
    ) -> LabourMarketSource | None:
        if source_id is None:
            return None

        result = await self.db.execute(
            select(LabourMarketSource).where(
                LabourMarketSource.id == source_id
            )
        )

        source = result.scalar_one_or_none()

        if source is None:
            raise EmergingSkillValidationError(
                "Labour-market source does not exist."
            )

        if not source.is_active:
            raise EmergingSkillValidationError(
                "Labour-market source is inactive."
            )

        return source

    async def create_trend(
        self,
        *,
        skill_id: UUID,
        government_unit_id: UUID | None,
        source_id: UUID | None,
        demand_count: int,
        growth_rate: float,
        trend_direction: str,
        rank: int | None,
        period_start: datetime,
        period_end: datetime,
    ) -> EmergingSkillTrend:
        if demand_count < 0:
            raise EmergingSkillValidationError(
                "Demand count cannot be negative."
            )

        if period_end < period_start:
            raise EmergingSkillValidationError(
                "Period end cannot be before period start."
            )

        if rank is not None and rank < 1:
            raise EmergingSkillValidationError(
                "Rank must be at least 1."
            )

        if not trend_direction.strip():
            raise EmergingSkillValidationError(
                "Trend direction is required."
            )

        await self.validate_skill(skill_id)
        await self.validate_unit(government_unit_id)
        await self.validate_source(source_id)

        trend = EmergingSkillTrend(
            skill_id=skill_id,
            government_unit_id=government_unit_id,
            source_id=source_id,
            demand_count=demand_count,
            growth_rate=growth_rate,
            trend_direction=trend_direction.strip().upper(),
            rank=rank,
            period_start=period_start,
            period_end=period_end,
        )

        self.db.add(trend)
        await self.db.commit()
        await self.db.refresh(trend)

        return trend

    async def list_trends(
        self,
        *,
        government_unit_id: UUID | None = None,
        skill_id: UUID | None = None,
        trend_direction: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EmergingSkillTrend]:
        stmt = select(EmergingSkillTrend).order_by(
            EmergingSkillTrend.growth_rate.desc(),
            EmergingSkillTrend.period_end.desc(),
        )

        if government_unit_id:
            stmt = stmt.where(
                EmergingSkillTrend.government_unit_id
                == government_unit_id
            )

        if skill_id:
            stmt = stmt.where(
                EmergingSkillTrend.skill_id == skill_id
            )

        if trend_direction:
            stmt = stmt.where(
                EmergingSkillTrend.trend_direction
                == trend_direction.strip().upper()
            )

        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)

        return list(result.scalars().all())