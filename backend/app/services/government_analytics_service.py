from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course_alignment import CourseAlignment
from app.models.emerging_skill_trend import EmergingSkillTrend
from app.models.government_unit import GovernmentUnit
from app.models.labour_market_snapshot import LabourMarketSnapshot
from app.models.placement_outcome import PlacementOutcome
from app.models.skill import Skill


class GovernmentAnalyticsServiceError(Exception):
    """Base government analytics service error."""


class GovernmentAnalyticsValidationError(GovernmentAnalyticsServiceError):
    """Raised when analytics input is invalid."""


class GovernmentAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

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
            raise GovernmentAnalyticsValidationError(
                "Government unit does not exist."
            )

        if not unit.is_active:
            raise GovernmentAnalyticsValidationError(
                "Government unit is inactive."
            )

        return unit

    async def demand_overview(
        self,
        government_unit_id: UUID | None = None,
    ) -> dict:
        await self.validate_unit(government_unit_id)

        stmt = select(
            func.coalesce(
                func.sum(LabourMarketSnapshot.demand_count),
                0,
            ).label("total_demand"),
            func.coalesce(
                func.sum(LabourMarketSnapshot.supply_count),
                0,
            ).label("total_supply"),
            func.count(LabourMarketSnapshot.id).label("records"),
        )

        if government_unit_id:
            stmt = stmt.where(
                LabourMarketSnapshot.government_unit_id
                == government_unit_id
            )

        result = await self.db.execute(stmt)
        row = result.one()

        total_demand = int(row.total_demand or 0)
        total_supply = int(row.total_supply or 0)

        return {
            "records": int(row.records or 0),
            "total_demand": total_demand,
            "total_supply": total_supply,
            "demand_supply_gap": total_demand - total_supply,
        }

    async def top_occupations(
        self,
        government_unit_id: UUID | None = None,
        limit: int = 10,
    ) -> list[dict]:
        await self.validate_unit(government_unit_id)

        stmt = select(
            LabourMarketSnapshot.occupation_name,
            func.sum(
                LabourMarketSnapshot.demand_count
            ).label("demand"),
            func.sum(
                LabourMarketSnapshot.supply_count
            ).label("supply"),
        ).group_by(
            LabourMarketSnapshot.occupation_name
        ).order_by(
            func.sum(
                LabourMarketSnapshot.demand_count
            ).desc()
        ).limit(limit)

        if government_unit_id:
            stmt = stmt.where(
                LabourMarketSnapshot.government_unit_id
                == government_unit_id
            )

        result = await self.db.execute(stmt)

        return [
            {
                "occupation_name": row.occupation_name,
                "demand": int(row.demand or 0),
                "supply": int(row.supply or 0),
                "gap": int((row.demand or 0) - (row.supply or 0)),
            }
            for row in result.all()
        ]

    async def emerging_skills(
        self,
        government_unit_id: UUID | None = None,
        limit: int = 10,
    ) -> list[dict]:
        await self.validate_unit(government_unit_id)

        stmt = select(
            Skill.id,
            Skill.name,
            func.max(
                EmergingSkillTrend.growth_rate
            ).label("growth_rate"),
            func.max(
                EmergingSkillTrend.demand_count
            ).label("demand_count"),
        ).join(
            EmergingSkillTrend,
            EmergingSkillTrend.skill_id == Skill.id,
        ).group_by(
            Skill.id,
            Skill.name,
        ).order_by(
            func.max(
                EmergingSkillTrend.growth_rate
            ).desc()
        ).limit(limit)

        if government_unit_id:
            stmt = stmt.where(
                EmergingSkillTrend.government_unit_id
                == government_unit_id
            )

        result = await self.db.execute(stmt)

        return [
            {
                "skill_id": row.id,
                "skill_name": row.name,
                "growth_rate": float(row.growth_rate or 0),
                "demand_count": int(row.demand_count or 0),
            }
            for row in result.all()
        ]

    async def placement_overview(
        self,
        government_unit_id: UUID | None = None,
    ) -> dict:
        await self.validate_unit(government_unit_id)

        stmt = select(
            func.coalesce(
                func.sum(PlacementOutcome.total_learners),
                0,
            ).label("learners"),
            func.coalesce(
                func.sum(PlacementOutcome.placed_learners),
                0,
            ).label("placed"),
        )

        if government_unit_id:
            stmt = stmt.where(
                PlacementOutcome.government_unit_id
                == government_unit_id
            )

        result = await self.db.execute(stmt)
        row = result.one()

        learners = int(row.learners or 0)
        placed = int(row.placed or 0)

        return {
            "total_learners": learners,
            "placed_learners": placed,
            "placement_rate": round(
                (placed / learners) * 100,
                2,
            ) if learners else 0.0,
        }

    async def course_alignment_overview(
        self,
        government_unit_id: UUID | None = None,
    ) -> dict:
        await self.validate_unit(government_unit_id)

        stmt = select(
            CourseAlignment.alignment_status,
            func.count(CourseAlignment.id).label("count"),
        ).group_by(
            CourseAlignment.alignment_status
        )

        if government_unit_id:
            stmt = stmt.where(
                CourseAlignment.government_unit_id
                == government_unit_id
            )

        result = await self.db.execute(stmt)

        counts = {
            str(row.alignment_status): int(row.count)
            for row in result.all()
        }

        return {
            "total": sum(counts.values()),
            "by_status": counts,
        }

    async def dashboard(
        self,
        government_unit_id: UUID | None = None,
    ) -> dict:
        """
        Combined government intelligence dashboard.

        Individual candidate PII is intentionally not returned.
        """
        await self.validate_unit(government_unit_id)

        demand = await self.demand_overview(government_unit_id)
        occupations = await self.top_occupations(
            government_unit_id,
            limit=10,
        )
        emerging = await self.emerging_skills(
            government_unit_id,
            limit=10,
        )
        placements = await self.placement_overview(
            government_unit_id
        )
        alignment = await self.course_alignment_overview(
            government_unit_id
        )

        return {
            "government_unit_id": government_unit_id,
            "demand_supply": demand,
            "top_occupations": occupations,
            "emerging_skills": emerging,
            "placement": placements,
            "course_alignment": alignment,
        }