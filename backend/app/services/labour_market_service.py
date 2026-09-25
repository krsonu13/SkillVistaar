from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.government_unit import GovernmentUnit
from app.models.labour_market_snapshot import LabourMarketSnapshot
from app.models.labour_market_source import LabourMarketSource
from app.models.skill import Skill


class LabourMarketServiceError(Exception):
    """Base labour-market service error."""


class LabourMarketValidationError(LabourMarketServiceError):
    """Raised when labour-market data is invalid."""


class LabourMarketNotFoundError(LabourMarketServiceError):
    """Raised when a labour-market record is not found."""


class LabourMarketService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    async def get_source(
        self,
        source_id: UUID,
    ) -> LabourMarketSource:
        result = await self.db.execute(
            select(LabourMarketSource).where(
                LabourMarketSource.id == source_id
            )
        )

        source = result.scalar_one_or_none()

        if source is None:
            raise LabourMarketNotFoundError(
                f"Labour-market source {source_id} not found."
            )

        return source

    async def create_source(
        self,
        *,
        name: str,
        source_type: str,
        organization_name: str | None = None,
        description: str | None = None,
        source_url: str | None = None,
        collection_method: str | None = None,
        reliability_score: float | None = None,
    ) -> LabourMarketSource:
        if not name or not name.strip():
            raise LabourMarketValidationError(
                "Source name is required."
            )

        if not source_type or not source_type.strip():
            raise LabourMarketValidationError(
                "Source type is required."
            )

        if reliability_score is not None and not (
            0 <= reliability_score <= 100
        ):
            raise LabourMarketValidationError(
                "Reliability score must be between 0 and 100."
            )

        source = LabourMarketSource(
            name=name.strip(),
            source_type=source_type.strip().upper(),
            organization_name=(
                organization_name.strip()
                if organization_name
                else None
            ),
            description=description,
            source_url=source_url,
            collection_method=(
                collection_method.strip()
                if collection_method
                else None
            ),
            reliability_score=reliability_score,
        )

        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)

        return source

    async def list_sources(
        self,
        *,
        source_type: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LabourMarketSource]:
        stmt = select(LabourMarketSource).order_by(
            LabourMarketSource.created_at.desc()
        )

        if active_only:
            stmt = stmt.where(
                LabourMarketSource.is_active.is_(True)
            )

        if source_type:
            stmt = stmt.where(
                LabourMarketSource.source_type
                == source_type.strip().upper()
            )

        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    async def validate_government_unit(
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
            raise LabourMarketValidationError(
                "Government unit does not exist."
            )

        if not unit.is_active:
            raise LabourMarketValidationError(
                "Government unit is inactive."
            )

        return unit

    async def validate_skill(
        self,
        skill_id: UUID | None,
    ) -> Skill | None:
        if skill_id is None:
            return None

        result = await self.db.execute(
            select(Skill).where(Skill.id == skill_id)
        )

        skill = result.scalar_one_or_none()

        if skill is None:
            raise LabourMarketValidationError(
                "Skill does not exist."
            )

        if not skill.is_active:
            raise LabourMarketValidationError(
                "Skill is inactive."
            )

        return skill

    async def validate_source(
        self,
        source_id: UUID | None,
    ) -> LabourMarketSource | None:
        if source_id is None:
            return None

        source = await self.get_source(source_id)

        if not source.is_active:
            raise LabourMarketValidationError(
                "Labour-market source is inactive."
            )

        return source

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    async def get_snapshot(
        self,
        snapshot_id: UUID,
    ) -> LabourMarketSnapshot:
        result = await self.db.execute(
            select(LabourMarketSnapshot).where(
                LabourMarketSnapshot.id == snapshot_id
            )
        )

        snapshot = result.scalar_one_or_none()

        if snapshot is None:
            raise LabourMarketNotFoundError(
                f"Labour-market snapshot {snapshot_id} not found."
            )

        return snapshot

    async def create_snapshot(
        self,
        *,
        government_unit_id: UUID | None,
        source_id: UUID | None,
        skill_id: UUID | None,
        occupation_code: str | None,
        occupation_name: str,
        sector: str | None,
        employment_type: str | None,
        workplace_type: str | None,
        experience_min: float | None,
        experience_max: float | None,
        demand_count: int,
        supply_count: int,
        average_salary: float | None,
        median_salary: float | None,
        currency: str,
        period_start: datetime,
        period_end: datetime,
        notes: str | None,
    ) -> LabourMarketSnapshot:
        if not occupation_name or not occupation_name.strip():
            raise LabourMarketValidationError(
                "Occupation name is required."
            )

        if demand_count < 0:
            raise LabourMarketValidationError(
                "Demand count cannot be negative."
            )

        if supply_count < 0:
            raise LabourMarketValidationError(
                "Supply count cannot be negative."
            )

        if experience_min is not None and experience_min < 0:
            raise LabourMarketValidationError(
                "Minimum experience cannot be negative."
            )

        if experience_max is not None and experience_max < 0:
            raise LabourMarketValidationError(
                "Maximum experience cannot be negative."
            )

        if (
            experience_min is not None
            and experience_max is not None
            and experience_max < experience_min
        ):
            raise LabourMarketValidationError(
                "Maximum experience cannot be lower than minimum experience."
            )

        if average_salary is not None and average_salary < 0:
            raise LabourMarketValidationError(
                "Average salary cannot be negative."
            )

        if median_salary is not None and median_salary < 0:
            raise LabourMarketValidationError(
                "Median salary cannot be negative."
            )

        if period_end < period_start:
            raise LabourMarketValidationError(
                "Period end cannot be before period start."
            )

        if len(currency) != 3:
            raise LabourMarketValidationError(
                "Currency must be a 3-letter code."
            )

        await self.validate_government_unit(government_unit_id)
        await self.validate_source(source_id)
        await self.validate_skill(skill_id)

        snapshot = LabourMarketSnapshot(
            government_unit_id=government_unit_id,
            source_id=source_id,
            skill_id=skill_id,
            occupation_code=occupation_code,
            occupation_name=occupation_name.strip(),
            sector=sector.strip() if sector else None,
            employment_type=(
                employment_type.strip()
                if employment_type
                else None
            ),
            workplace_type=(
                workplace_type.strip()
                if workplace_type
                else None
            ),
            experience_min=experience_min,
            experience_max=experience_max,
            demand_count=demand_count,
            supply_count=supply_count,
            average_salary=average_salary,
            median_salary=median_salary,
            currency=currency.upper(),
            period_start=period_start,
            period_end=period_end,
            notes=notes,
        )

        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)

        return snapshot

    async def list_snapshots(
        self,
        *,
        government_unit_id: UUID | None = None,
        skill_id: UUID | None = None,
        occupation_name: str | None = None,
        sector: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LabourMarketSnapshot]:
        stmt = select(LabourMarketSnapshot).order_by(
            LabourMarketSnapshot.period_end.desc(),
            LabourMarketSnapshot.created_at.desc(),
        )

        if government_unit_id:
            stmt = stmt.where(
                LabourMarketSnapshot.government_unit_id
                == government_unit_id
            )

        if skill_id:
            stmt = stmt.where(
                LabourMarketSnapshot.skill_id == skill_id
            )

        if occupation_name:
            stmt = stmt.where(
                LabourMarketSnapshot.occupation_name.ilike(
                    f"%{occupation_name.strip()}%"
                )
            )

        if sector:
            stmt = stmt.where(
                LabourMarketSnapshot.sector.ilike(
                    f"%{sector.strip()}%"
                )
            )

        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def get_demand_supply_summary(
        self,
        *,
        government_unit_id: UUID | None = None,
        skill_id: UUID | None = None,
    ) -> dict:
        stmt = select(
            func.coalesce(
                func.sum(LabourMarketSnapshot.demand_count),
                0,
            ).label("total_demand"),
            func.coalesce(
                func.sum(LabourMarketSnapshot.supply_count),
                0,
            ).label("total_supply"),
            func.count(LabourMarketSnapshot.id).label(
                "records"
            ),
        )

        if government_unit_id:
            stmt = stmt.where(
                LabourMarketSnapshot.government_unit_id
                == government_unit_id
            )

        if skill_id:
            stmt = stmt.where(
                LabourMarketSnapshot.skill_id == skill_id
            )

        result = await self.db.execute(stmt)
        row = result.one()

        total_demand = int(row.total_demand or 0)
        total_supply = int(row.total_supply or 0)

        return {
            "total_demand": total_demand,
            "total_supply": total_supply,
            "demand_supply_gap": total_demand - total_supply,
            "records": int(row.records or 0),
        }