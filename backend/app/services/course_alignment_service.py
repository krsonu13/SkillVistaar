from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.course_alignment import CourseAlignment
from app.models.government_unit import GovernmentUnit
from app.models.skill import Skill


class CourseAlignmentServiceError(Exception):
    pass


class CourseAlignmentValidationError(
    CourseAlignmentServiceError
):
    pass


class CourseAlignmentNotFoundError(
    CourseAlignmentServiceError
):
    pass


class CourseAlignmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_alignment(self, alignment_id: UUID):
        result = await self.db.execute(
            select(CourseAlignment).where(
                CourseAlignment.id == alignment_id
            )
        )

        alignment = result.scalar_one_or_none()

        if alignment is None:
            raise CourseAlignmentNotFoundError(
                "Course alignment record not found."
            )

        return alignment

    async def validate_course(self, course_id: UUID):
        result = await self.db.execute(
            select(Course).where(
                Course.id == course_id,
            )
        )

        course = result.scalar_one_or_none()

        if course is None:
            raise CourseAlignmentValidationError(
                "Course not found."
            )

        return course

    async def validate_skill(self, skill_id: UUID):
        result = await self.db.execute(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        skill = result.scalar_one_or_none()

        if skill is None:
            raise CourseAlignmentValidationError(
                "Skill not found or inactive."
            )

        return skill

    async def validate_unit(
        self,
        government_unit_id: UUID | None,
    ):
        if government_unit_id is None:
            return None

        result = await self.db.execute(
            select(GovernmentUnit).where(
                GovernmentUnit.id == government_unit_id,
                GovernmentUnit.is_active.is_(True),
            )
        )

        unit = result.scalar_one_or_none()

        if unit is None:
            raise CourseAlignmentValidationError(
                "Government unit not found or inactive."
            )

        return unit

    async def create_alignment(
        self,
        *,
        course_id: UUID,
        skill_id: UUID,
        government_unit_id: UUID | None,
        demand_score: float,
        skill_coverage_score: float,
        alignment_score: float,
        alignment_status: str,
        recommended_action: str | None,
    ):
        for value, name in (
            (demand_score, "Demand score"),
            (skill_coverage_score, "Skill coverage score"),
            (alignment_score, "Alignment score"),
        ):
            if not 0 <= value <= 100:
                raise CourseAlignmentValidationError(
                    f"{name} must be between 0 and 100."
                )

        await self.validate_course(course_id)
        await self.validate_skill(skill_id)
        await self.validate_unit(government_unit_id)

        existing = await self.db.execute(
            select(CourseAlignment).where(
                CourseAlignment.course_id == course_id,
                CourseAlignment.skill_id == skill_id,
                CourseAlignment.government_unit_id
                == government_unit_id,
            )
        )

        if existing.scalar_one_or_none() is not None:
            raise CourseAlignmentValidationError(
                "Course alignment already exists."
            )

        alignment = CourseAlignment(
            course_id=course_id,
            skill_id=skill_id,
            government_unit_id=government_unit_id,
            demand_score=demand_score,
            skill_coverage_score=skill_coverage_score,
            alignment_score=alignment_score,
            alignment_status=alignment_status.upper(),
            recommended_action=recommended_action,
        )

        self.db.add(alignment)
        await self.db.commit()
        await self.db.refresh(alignment)

        return alignment

    async def list_alignments(
        self,
        *,
        course_id: UUID | None = None,
        skill_id: UUID | None = None,
        government_unit_id: UUID | None = None,
        alignment_status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ):
        stmt = select(CourseAlignment)

        if course_id:
            stmt = stmt.where(
                CourseAlignment.course_id == course_id
            )

        if skill_id:
            stmt = stmt.where(
                CourseAlignment.skill_id == skill_id
            )

        if government_unit_id:
            stmt = stmt.where(
                CourseAlignment.government_unit_id
                == government_unit_id
            )

        if alignment_status:
            stmt = stmt.where(
                CourseAlignment.alignment_status
                == alignment_status.upper()
            )

        stmt = (
            stmt.order_by(
                CourseAlignment.alignment_score.desc()
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())