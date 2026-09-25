from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, CourseStatus
from app.models.course_skill import CourseSkill
from app.models.institution_profile import InstitutionVerificationStatus
from app.models.skill import Skill
from app.models.user import User
from app.services.course_service import (
    CourseAccessDeniedError,
    CourseNotFoundError,
    CourseService,
    CourseServiceError,
    CourseValidationError,
)


class CourseSkillServiceError(CourseServiceError):
    """Base exception for course-skill mapping errors."""


class CourseSkillNotFoundError(CourseSkillServiceError):
    """Course-skill mapping was not found."""


class CourseSkillAccessDeniedError(CourseSkillServiceError):
    """User cannot manage or view the mapping."""


class CourseSkillValidationError(CourseSkillServiceError):
    """Course-skill mapping data is invalid."""


class CourseSkillService:
    VALID_IMPORTANCE = {
        "CORE",
        "IMPORTANT",
        "OPTIONAL",
    }

    VALID_PROFICIENCY = {
        "BEGINNER",
        "INTERMEDIATE",
        "ADVANCED",
        "EXPERT",
    }

    @staticmethod
    async def get_mapping(
        db: AsyncSession,
        mapping_id: UUID,
    ) -> CourseSkill:
        result = await db.execute(
            select(CourseSkill).where(
                CourseSkill.id == mapping_id
            )
        )

        mapping = result.scalar_one_or_none()

        if not mapping:
            raise CourseSkillNotFoundError(
                "Course skill mapping not found."
            )

        return mapping

    @staticmethod
    async def get_course(
        db: AsyncSession,
        course_id: UUID,
    ) -> Course:
        result = await db.execute(
            select(Course).where(Course.id == course_id)
        )

        course = result.scalar_one_or_none()

        if not course:
            raise CourseNotFoundError(
                "Course not found."
            )

        return course

    @staticmethod
    async def get_active_skill(
        db: AsyncSession,
        skill_id: UUID,
    ) -> Skill:
        result = await db.execute(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        skill = result.scalar_one_or_none()

        if not skill:
            raise CourseSkillValidationError(
                "Skill not found or inactive."
            )

        return skill

    @classmethod
    async def ensure_course_manager(
        cls,
        db: AsyncSession,
        course: Course,
        current_user: User,
    ):
        return await CourseService.require_institution_manager(
            db,
            course.institution_profile_id,
            current_user,
        )

    @classmethod
    async def ensure_mapping_course(
        cls,
        db: AsyncSession,
        mapping: CourseSkill,
        course_id: UUID,
    ) -> Course:
        if mapping.course_id != course_id:
            raise CourseSkillValidationError(
                "Course skill mapping does not belong to this course."
            )

        return await cls.get_course(db, course_id)

    @classmethod
    async def validate_mapping_values(
        cls,
        importance: str | None,
        proficiency_level: str | None,
        module_name: str | None,
        description: str | None,
    ) -> None:
        if importance is not None:
            importance = importance.upper()

            if importance not in cls.VALID_IMPORTANCE:
                raise CourseSkillValidationError(
                    "Invalid skill importance."
                )

        if proficiency_level is not None:
            proficiency_level = proficiency_level.upper()

            if proficiency_level not in cls.VALID_PROFICIENCY:
                raise CourseSkillValidationError(
                    "Invalid proficiency level."
                )

        if module_name is not None and len(module_name.strip()) > 255:
            raise CourseSkillValidationError(
                "Module name is too long."
            )

        if description is not None and len(description.strip()) > 1000:
            raise CourseSkillValidationError(
                "Skill mapping description is too long."
            )

    @staticmethod
    async def ensure_unique_mapping(
        db: AsyncSession,
        course_id: UUID,
        skill_id: UUID,
        exclude_mapping_id: UUID | None = None,
    ) -> None:
        query = select(CourseSkill.id).where(
            CourseSkill.course_id == course_id,
            CourseSkill.skill_id == skill_id,
        )

        if exclude_mapping_id:
            query = query.where(
                CourseSkill.id != exclude_mapping_id
            )

        result = await db.execute(query)

        if result.scalar_one_or_none():
            raise CourseSkillValidationError(
                "This skill is already mapped to the course."
            )

    @staticmethod
    async def mark_course_for_review(
        db: AsyncSession,
        course: Course,
    ) -> None:
        if course.status == CourseStatus.PUBLISHED.value:
            course.status = CourseStatus.PENDING_REVIEW.value
            course.published_at = None

    @classmethod
    async def add_skill(
        cls,
        db: AsyncSession,
        course_id: UUID,
        skill_id: UUID,
        importance: str,
        proficiency_level: str,
        is_mandatory: bool,
        module_name: str | None,
        description: str | None,
        current_user: User,
    ) -> CourseSkill:
        course = await cls.get_course(db, course_id)

        await cls.ensure_course_manager(
            db,
            course,
            current_user,
        )

        if course.status in {
            CourseStatus.CLOSED.value,
            CourseStatus.ARCHIVED.value,
        }:
            raise CourseSkillValidationError(
                "Skills cannot be modified on closed or archived courses."
            )

        importance = importance.upper()
        proficiency_level = proficiency_level.upper()

        await cls.validate_mapping_values(
            importance,
            proficiency_level,
            module_name,
            description,
        )

        await cls.get_active_skill(
            db,
            skill_id,
        )

        await cls.ensure_unique_mapping(
            db,
            course_id,
            skill_id,
        )

        mapping = CourseSkill(
            course_id=course_id,
            skill_id=skill_id,
            importance=importance,
            proficiency_level=proficiency_level,
            is_mandatory=is_mandatory,
            module_name=(
                module_name.strip()
                if module_name
                else None
            ),
            description=(
                description.strip()
                if description
                else None
            ),
        )

        db.add(mapping)

        await cls.mark_course_for_review(
            db,
            course,
        )

        await db.commit()
        await db.refresh(mapping)

        return mapping

    @classmethod
    async def update_skill(
        cls,
        db: AsyncSession,
        mapping_id: UUID,
        importance: str | None,
        proficiency_level: str | None,
        is_mandatory: bool | None,
        module_name: str | None,
        description: str | None,
        current_user: User,
    ) -> CourseSkill:
        mapping = await cls.get_mapping(
            db,
            mapping_id,
        )

        course = await cls.get_course(
            db,
            mapping.course_id,
        )

        await cls.ensure_course_manager(
            db,
            course,
            current_user,
        )

        if course.status in {
            CourseStatus.CLOSED.value,
            CourseStatus.ARCHIVED.value,
        }:
            raise CourseSkillValidationError(
                "Skills cannot be modified on closed or archived courses."
            )

        await cls.validate_mapping_values(
            importance,
            proficiency_level,
            module_name,
            description,
        )

        if importance is not None:
            mapping.importance = importance.upper()

        if proficiency_level is not None:
            mapping.proficiency_level = proficiency_level.upper()

        if is_mandatory is not None:
            mapping.is_mandatory = is_mandatory

        if module_name is not None:
            mapping.module_name = module_name.strip()

        if description is not None:
            mapping.description = description.strip()

        await cls.mark_course_for_review(
            db,
            course,
        )

        await db.commit()
        await db.refresh(mapping)

        return mapping

    @classmethod
    async def remove_skill(
        cls,
        db: AsyncSession,
        mapping_id: UUID,
        current_user: User,
    ) -> None:
        mapping = await cls.get_mapping(
            db,
            mapping_id,
        )

        course = await cls.get_course(
            db,
            mapping.course_id,
        )

        await cls.ensure_course_manager(
            db,
            course,
            current_user,
        )

        if course.status in {
            CourseStatus.CLOSED.value,
            CourseStatus.ARCHIVED.value,
        }:
            raise CourseSkillValidationError(
                "Skills cannot be removed from closed or archived courses."
            )

        await db.delete(mapping)

        await cls.mark_course_for_review(
            db,
            course,
        )

        await db.commit()

    @classmethod
    async def list_course_skills(
        cls,
        db: AsyncSession,
        course_id: UUID,
        current_user: User | None = None,
        include_all: bool = False,
    ) -> list[CourseSkill]:
        course = await cls.get_course(
            db,
            course_id,
        )

        # Public users may only see skills for published courses
        # belonging to an active, approved training institution.
        if course.status == CourseStatus.PUBLISHED.value:
            from app.models.institution_profile import InstitutionProfile

            institution_result = await db.execute(
                select(InstitutionProfile).where(
                    InstitutionProfile.id
                    == course.institution_profile_id,
                    InstitutionProfile.is_active.is_(True),
                    InstitutionProfile.verification_status
                    == InstitutionVerificationStatus.APPROVED.value,
                )
            )

            institution = institution_result.scalar_one_or_none()

            if not institution:
                if not current_user:
                    raise CourseSkillAccessDeniedError(
                        "This course is not publicly available."
                    )

                await cls.ensure_course_manager(
                    db,
                    course,
                    current_user,
                )
        else:
            if not current_user:
                raise CourseSkillAccessDeniedError(
                    "Authentication is required."
                )

            await cls.ensure_course_manager(
                db,
                course,
                current_user,
            )

        query = select(CourseSkill).where(
            CourseSkill.course_id == course_id
        )

        if not include_all:
            query = query.where(
                CourseSkill.is_mandatory.is_(True)
            )

        query = query.order_by(
            CourseSkill.is_mandatory.desc(),
            CourseSkill.created_at.asc(),
        )

        result = await db.execute(query)

        return list(result.scalars().all())

    @classmethod
    async def get_skill_ids_for_course(
        cls,
        db: AsyncSession,
        course_id: UUID,
    ) -> list[UUID]:
        course = await cls.get_course(
            db,
            course_id,
        )

        if course.status != CourseStatus.PUBLISHED.value:
            return []

        result = await db.execute(
            select(CourseSkill.skill_id)
            .where(
                CourseSkill.course_id == course_id,
                CourseSkill.is_mandatory.is_(True),
            )
            .order_by(
                CourseSkill.created_at.asc()
            )
        )

        return list(result.scalars().all())
