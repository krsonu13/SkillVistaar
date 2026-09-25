from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.government_unit import GovernmentUnit
from app.models.institution_profile import InstitutionProfile
from app.models.labour_market_source import LabourMarketSource
from app.models.placement_outcome import PlacementOutcome


class PlacementOutcomeServiceError(Exception):
    """Base placement outcome service error."""


class PlacementOutcomeValidationError(PlacementOutcomeServiceError):
    """Raised when placement outcome data is invalid."""


class PlacementOutcomeNotFoundError(PlacementOutcomeServiceError):
    """Raised when a placement outcome is not found."""


class PlacementOutcomeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_outcome(self, outcome_id: UUID) -> PlacementOutcome:
        result = await self.db.execute(
            select(PlacementOutcome).where(PlacementOutcome.id == outcome_id)
        )
        outcome = result.scalar_one_or_none()

        if outcome is None:
            raise PlacementOutcomeNotFoundError(
                f"Placement outcome {outcome_id} not found."
            )

        return outcome

    async def validate_institution(
        self,
        institution_profile_id: UUID,
    ) -> InstitutionProfile:
        result = await self.db.execute(
            select(InstitutionProfile).where(
                InstitutionProfile.id == institution_profile_id
            )
        )
        institution = result.scalar_one_or_none()

        if institution is None:
            raise PlacementOutcomeValidationError(
                "Institution profile does not exist."
            )

        return institution

    async def validate_course(
        self,
        course_id: UUID | None,
    ) -> Course | None:
        if course_id is None:
            return None

        result = await self.db.execute(
            select(Course).where(Course.id == course_id)
        )
        course = result.scalar_one_or_none()

        if course is None:
            raise PlacementOutcomeValidationError(
                "Course does not exist."
            )

        return course

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
            raise PlacementOutcomeValidationError(
                "Government unit does not exist."
            )

        if not unit.is_active:
            raise PlacementOutcomeValidationError(
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
            raise PlacementOutcomeValidationError(
                "Labour-market source does not exist."
            )

        return source

    @staticmethod
    def _validate_values(
        total_learners: int,
        placed_learners: int,
        employment_rate: float,
        average_salary: float | None,
        median_salary: float | None,
        period_start: date,
        period_end: date,
    ) -> None:
        if total_learners < 0:
            raise PlacementOutcomeValidationError(
                "Total learners cannot be negative."
            )

        if placed_learners < 0:
            raise PlacementOutcomeValidationError(
                "Placed learners cannot be negative."
            )

        if placed_learners > total_learners:
            raise PlacementOutcomeValidationError(
                "Placed learners cannot exceed total learners."
            )

        if not 0 <= employment_rate <= 100:
            raise PlacementOutcomeValidationError(
                "Employment rate must be between 0 and 100."
            )

        if average_salary is not None and average_salary < 0:
            raise PlacementOutcomeValidationError(
                "Average salary cannot be negative."
            )

        if median_salary is not None and median_salary < 0:
            raise PlacementOutcomeValidationError(
                "Median salary cannot be negative."
            )

        if period_end < period_start:
            raise PlacementOutcomeValidationError(
                "Period end cannot be before period start."
            )

    async def create_outcome(
        self,
        *,
        institution_profile_id: UUID,
        course_id: UUID | None,
        government_unit_id: UUID | None,
        occupation_name: str,
        sector: str | None,
        total_learners: int,
        placed_learners: int,
        employment_rate: float,
        average_salary: float | None,
        median_salary: float | None,
        currency: str,
        period_start: date,
        period_end: date,
        source_id: UUID | None,
        notes: str | None,
    ) -> PlacementOutcome:
        if not occupation_name.strip():
            raise PlacementOutcomeValidationError(
                "Occupation name is required."
            )

        if len(currency) != 3:
            raise PlacementOutcomeValidationError(
                "Currency must use a 3-letter ISO-style code."
            )

        self._validate_values(
            total_learners,
            placed_learners,
            employment_rate,
            average_salary,
            median_salary,
            period_start,
            period_end,
        )

        await self.validate_institution(institution_profile_id)
        await self.validate_course(course_id)
        await self.validate_government_unit(government_unit_id)
        await self.validate_source(source_id)

        outcome = PlacementOutcome(
            institution_profile_id=institution_profile_id,
            course_id=course_id,
            government_unit_id=government_unit_id,
            occupation_name=occupation_name.strip(),
            sector=sector.strip() if sector else None,
            total_learners=total_learners,
            placed_learners=placed_learners,
            employment_rate=employment_rate,
            average_salary=average_salary,
            median_salary=median_salary,
            currency=currency.upper(),
            period_start=period_start,
            period_end=period_end,
            source_id=source_id,
            notes=notes,
        )

        self.db.add(outcome)
        await self.db.commit()
        await self.db.refresh(outcome)

        return outcome

    async def list_outcomes(
        self,
        *,
        institution_profile_id: UUID | None = None,
        course_id: UUID | None = None,
        government_unit_id: UUID | None = None,
        occupation_name: str | None = None,
        sector: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PlacementOutcome]:
        stmt = select(PlacementOutcome).order_by(
            PlacementOutcome.period_end.desc(),
            PlacementOutcome.created_at.desc(),
        )

        if institution_profile_id:
            stmt = stmt.where(
                PlacementOutcome.institution_profile_id
                == institution_profile_id
            )

        if course_id:
            stmt = stmt.where(PlacementOutcome.course_id == course_id)

        if government_unit_id:
            stmt = stmt.where(
                PlacementOutcome.government_unit_id == government_unit_id
            )

        if occupation_name:
            stmt = stmt.where(
                PlacementOutcome.occupation_name.ilike(
                    f"%{occupation_name.strip()}%"
                )
            )

        if sector:
            stmt = stmt.where(
                PlacementOutcome.sector.ilike(f"%{sector.strip()}%")
            )

        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_summary(
        self,
        *,
        government_unit_id: UUID | None = None,
        course_id: UUID | None = None,
        institution_profile_id: UUID | None = None,
        sector: str | None = None,
    ) -> dict:
        outcomes = await self.list_outcomes(
            government_unit_id=government_unit_id,
            course_id=course_id,
            institution_profile_id=institution_profile_id,
            sector=sector,
            limit=10000,
            offset=0,
        )

        total_learners = sum(item.total_learners for item in outcomes)
        placed_learners = sum(item.placed_learners for item in outcomes)

        calculated_rate = (
            (placed_learners / total_learners) * 100
            if total_learners
            else 0.0
        )

        salaries = [
            item.average_salary
            for item in outcomes
            if item.average_salary is not None
        ]

        average_salary = (
            sum(salaries) / len(salaries)
            if salaries
            else None
        )

        return {
            "record_count": len(outcomes),
            "total_learners": total_learners,
            "placed_learners": placed_learners,
            "overall_employment_rate": round(calculated_rate, 2),
            "average_salary": (
                round(average_salary, 2)
                if average_salary is not None
                else None
            ),
        }