from datetime import date, datetime, timezone
from decimal import Decimal
import math
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, CourseStatus
from app.models.institution_profile import (
    InstitutionProfile,
    InstitutionVerificationStatus,
)
from app.models.organization import Organization, OrganizationType
from app.models.organization_member import (
    OrganizationMember,
    OrganizationMemberRole,
)
from app.models.user import User
from app.schemas.course import CourseCreate, CourseUpdate


class CourseServiceError(Exception):
    """Base exception for course service errors."""


class CourseNotFoundError(CourseServiceError):
    """Course does not exist."""


class CourseAccessDeniedError(CourseServiceError):
    """User is not authorized to access the course."""


class CourseValidationError(CourseServiceError):
    """Course data is invalid."""


class CourseService:
    MANAGER_ROLES = {
        OrganizationMemberRole.ORG_ADMIN.value,
        OrganizationMemberRole.INSTITUTION_ADMIN.value,
    }

    @staticmethod
    async def get_course(
        db: AsyncSession,
        course_id: uuid.UUID,
    ) -> Course:
        result = await db.execute(
            select(Course).where(Course.id == course_id)
        )
        course = result.scalar_one_or_none()

        if not course:
            raise CourseNotFoundError("Course not found.")

        return course

    @staticmethod
    async def get_institution(
        db: AsyncSession,
        institution_profile_id: uuid.UUID,
    ) -> InstitutionProfile:
        result = await db.execute(
            select(InstitutionProfile)
            .join(
                Organization,
                Organization.id == InstitutionProfile.organization_id,
            )
            .where(
                InstitutionProfile.id == institution_profile_id,
                Organization.organization_type
                == OrganizationType.TRAINING_INSTITUTE.value,
            )
        )

        institution = result.scalar_one_or_none()

        if not institution:
            raise CourseValidationError(
                "Training institution not found."
            )

        return institution

    @classmethod
    async def require_institution_manager(
        cls,
        db: AsyncSession,
        institution_profile_id: uuid.UUID,
        current_user: User,
    ) -> InstitutionProfile:
        if not current_user:
            raise CourseAccessDeniedError(
                "Authentication is required."
            )

        institution = await cls.get_institution(
            db,
            institution_profile_id,
        )

        if not institution.is_active:
            raise CourseAccessDeniedError(
                "This institution is inactive."
            )

        if institution.verification_status in {
            InstitutionVerificationStatus.SUSPENDED.value,
            InstitutionVerificationStatus.REVOKED.value,
        }:
            raise CourseAccessDeniedError(
                "This institution is suspended or revoked."
            )

        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id
                == institution.organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.is_active.is_(True),
                OrganizationMember.role_code.in_(cls.MANAGER_ROLES),
            )
        )

        membership = result.scalar_one_or_none()

        if not membership:
            raise CourseAccessDeniedError(
                "You are not authorized to manage this institution."
            )

        return institution

    @staticmethod
    def validate_dates(data: CourseCreate | CourseUpdate) -> None:
        if (
            data.batch_start
            and data.batch_end
            and data.batch_end < data.batch_start
        ):
            raise CourseValidationError(
                "Batch end date cannot be before batch start date."
            )

        if (
            data.admission_start
            and data.admission_end
            and data.admission_end < data.admission_start
        ):
            raise CourseValidationError(
                "Admission end date cannot be before admission start date."
            )

        if (
            data.admission_end
            and data.batch_start
            and data.admission_end > data.batch_start
        ):
            raise CourseValidationError(
                "Admission must close on or before the batch starts."
            )

    @staticmethod
    def validate_course_values(
        data: CourseCreate | CourseUpdate,
    ) -> None:
        if data.duration_value is not None and data.duration_value <= 0:
            raise CourseValidationError(
                "Duration must be greater than zero."
            )

        if data.seats is not None and data.seats <= 0:
            raise CourseValidationError(
                "Seats must be greater than zero."
            )

        if data.fee is not None and data.fee < Decimal("0"):
            raise CourseValidationError(
                "Course fee cannot be negative."
            )

        if data.placement_rate is not None and not (
            Decimal("0")
            <= data.placement_rate
            <= Decimal("100")
        ):
            raise CourseValidationError(
                "Placement rate must be between 0 and 100."
            )

        if data.title is not None and not data.title.strip():
            raise CourseValidationError(
                "Course title cannot be empty."
            )

    @staticmethod
    async def ensure_unique_course(
        db: AsyncSession,
        institution_profile_id: uuid.UUID,
        title: str | None = None,
        course_code: str | None = None,
        exclude_course_id: uuid.UUID | None = None,
    ) -> None:
        if title:
            query = select(Course.id).where(
                Course.institution_profile_id == institution_profile_id,
                func.lower(Course.title) == title.strip().lower(),
            )

            if exclude_course_id:
                query = query.where(Course.id != exclude_course_id)

            result = await db.execute(query)

            if result.scalar_one_or_none():
                raise CourseValidationError(
                    "A course with this title already exists "
                    "in this institution."
                )

        if course_code:
            query = select(Course.id).where(
                func.lower(Course.course_code)
                == course_code.strip().lower()
            )

            if exclude_course_id:
                query = query.where(Course.id != exclude_course_id)

            result = await db.execute(query)

            if result.scalar_one_or_none():
                raise CourseValidationError(
                    "This course code is already in use."
                )

    @classmethod
    async def create_course(
        cls,
        db: AsyncSession,
        data: CourseCreate,
        current_user: User,
    ) -> Course:
        institution = await cls.require_institution_manager(
            db,
            data.institution_profile_id,
            current_user,
        )

        cls.validate_dates(data)
        cls.validate_course_values(data)

        await cls.ensure_unique_course(
            db,
            institution.id,
            data.title,
            data.course_code,
        )

        course = Course(
            institution_profile_id=institution.id,
            course_code=(
                data.course_code.strip()
                if data.course_code
                else None
            ),
            title=data.title.strip(),
            short_description=data.short_description,
            description=data.description,
            course_level=data.course_level,
            delivery_mode=data.delivery_mode,
            duration_value=data.duration_value,
            duration_unit=data.duration_unit,
            fee=data.fee,
            currency=data.currency,
            eligibility=data.eligibility,
            seats=data.seats,
            batch_start=data.batch_start,
            batch_end=data.batch_end,
            admission_start=data.admission_start,
            admission_end=data.admission_end,
            syllabus=data.syllabus,
            placement_support=data.placement_support,
            placement_rate=data.placement_rate,
            status=CourseStatus.DRAFT.value,
            is_featured=False,
        )

        db.add(course)
        await db.commit()
        await db.refresh(course)

        return course

    @classmethod
    async def update_course(
        cls,
        db: AsyncSession,
        course_id: uuid.UUID,
        data: CourseUpdate,
        current_user: User,
    ) -> Course:
        course = await cls.get_course(db, course_id)

        institution = await cls.require_institution_manager(
            db,
            course.institution_profile_id,
            current_user,
        )

        if course.status in {
            CourseStatus.CLOSED.value,
            CourseStatus.ARCHIVED.value,
        }:
            raise CourseValidationError(
                "Closed or archived courses cannot be edited."
            )

        cls.validate_dates(data)
        cls.validate_course_values(data)

        values = data.model_dump(exclude_unset=True)

        if "title" in values and values["title"]:
            values["title"] = values["title"].strip()

        if "course_code" in values and values["course_code"]:
            values["course_code"] = values["course_code"].strip()

        await cls.ensure_unique_course(
            db,
            institution.id,
            values.get("title", course.title),
            values.get("course_code", course.course_code),
            exclude_course_id=course.id,
        )

        protected_fields = {
            "id",
            "institution_profile_id",
            "status",
            "published_at",
            "closed_at",
            "created_at",
            "updated_at",
        }

        for field, value in values.items():
            if field not in protected_fields:
                setattr(course, field, value)

        if course.status == CourseStatus.PUBLISHED.value:
            course.status = CourseStatus.PENDING_REVIEW.value
            course.published_at = None

        await db.commit()
        await db.refresh(course)

        return course

    @classmethod
    async def submit_for_review(
        cls,
        db: AsyncSession,
        course_id: uuid.UUID,
        current_user: User,
    ) -> Course:
        course = await cls.get_course(db, course_id)

        await cls.require_institution_manager(
            db,
            course.institution_profile_id,
            current_user,
        )

        if course.status not in {
            CourseStatus.DRAFT.value,
            CourseStatus.CLOSED.value,
        }:
            raise CourseValidationError(
                "Only draft or closed courses can be submitted for review."
            )

        course.status = CourseStatus.PENDING_REVIEW.value

        await db.commit()
        await db.refresh(course)

        return course

    @classmethod
    async def publish_course(
        cls,
        db: AsyncSession,
        course_id: uuid.UUID,
        current_user: User,
    ) -> Course:
        course = await cls.get_course(db, course_id)

        institution = await cls.require_institution_manager(
            db,
            course.institution_profile_id,
            current_user,
        )

        if course.status != CourseStatus.PENDING_REVIEW.value:
            raise CourseValidationError(
                "Only courses pending review can be published."
            )

        if institution.verification_status != (
            InstitutionVerificationStatus.APPROVED.value
        ):
            raise CourseValidationError(
                "The institution must be approved before publishing courses."
            )

        if not institution.is_active:
            raise CourseValidationError(
                "The institution is inactive."
            )

        if not course.title.strip():
            raise CourseValidationError(
                "Course title is required."
            )

        if not course.description and not course.short_description:
            raise CourseValidationError(
                "Course description is required."
            )

        if course.duration_value <= 0:
            raise CourseValidationError(
                "Course duration must be greater than zero."
            )

        if course.seats is None or course.seats <= 0:
            raise CourseValidationError(
                "Course seats must be greater than zero."
            )

        if (
            course.batch_start
            and course.batch_end
            and course.batch_end < course.batch_start
        ):
            raise CourseValidationError(
                "Invalid batch dates."
            )

        if (
            course.admission_start
            and course.admission_end
            and course.admission_end < course.admission_start
        ):
            raise CourseValidationError(
                "Invalid admission dates."
            )

        # A published course must have at least one mapped skill.
        from app.models.course_skill import CourseSkill

        skill_result = await db.execute(
            select(func.count(CourseSkill.id)).where(
                CourseSkill.course_id == course.id
            )
        )

        skill_count = skill_result.scalar_one()

        if skill_count < 1:
            raise CourseValidationError(
                "At least one skill must be mapped before publishing."
            )

        course.status = CourseStatus.PUBLISHED.value
        course.published_at = datetime.now(timezone.utc)
        course.closed_at = None

        await db.commit()
        await db.refresh(course)

        return course

    @classmethod
    async def close_course(
        cls,
        db: AsyncSession,
        course_id: uuid.UUID,
        current_user: User,
    ) -> Course:
        course = await cls.get_course(db, course_id)

        await cls.require_institution_manager(
            db,
            course.institution_profile_id,
            current_user,
        )

        if course.status != CourseStatus.PUBLISHED.value:
            raise CourseValidationError(
                "Only published courses can be closed."
            )

        course.status = CourseStatus.CLOSED.value
        course.closed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(course)

        return course

    @classmethod
    async def archive_course(
        cls,
        db: AsyncSession,
        course_id: uuid.UUID,
        current_user: User,
    ) -> Course:
        course = await cls.get_course(db, course_id)

        await cls.require_institution_manager(
            db,
            course.institution_profile_id,
            current_user,
        )

        if course.status not in {
            CourseStatus.CLOSED.value,
            CourseStatus.DRAFT.value,
        }:
            raise CourseValidationError(
                "Only closed or draft courses can be archived."
            )

        course.status = CourseStatus.ARCHIVED.value

        await db.commit()
        await db.refresh(course)

        return course

    @classmethod
    async def get_course_for_user(
        cls,
        db: AsyncSession,
        course_id: uuid.UUID,
        current_user: User | None = None,
    ) -> Course:
        course = await cls.get_course(db, course_id)

        if course.status != CourseStatus.PUBLISHED.value:
            if not current_user:
                raise CourseAccessDeniedError(
                    "Authentication is required to access this course."
                )

            await cls.require_institution_manager(
                db,
                course.institution_profile_id,
                current_user,
            )

        return course

    @classmethod
    async def list_courses(
        cls,
        db: AsyncSession,
        institution_profile_id: uuid.UUID | None = None,
        keyword: str | None = None,
        delivery_mode: str | None = None,
        course_level: str | None = None,
        city: str | None = None,
        state: str | None = None,
        admission_open: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Course], int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)

        conditions = [
            Course.status == CourseStatus.PUBLISHED.value,
            InstitutionProfile.is_active.is_(True),
            InstitutionProfile.verification_status
            == InstitutionVerificationStatus.APPROVED.value,
            Organization.is_active.is_(True),
            Organization.organization_type
            == OrganizationType.TRAINING_INSTITUTE.value,
        ]

        if institution_profile_id:
            conditions.append(
                Course.institution_profile_id
                == institution_profile_id
            )

        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    Course.title.ilike(pattern),
                    Course.short_description.ilike(pattern),
                    Course.description.ilike(pattern),
                )
            )

        if delivery_mode:
            conditions.append(
                Course.delivery_mode == delivery_mode
            )

        if course_level:
            conditions.append(
                Course.course_level == course_level
            )

        if city:
            conditions.append(
                func.lower(InstitutionProfile.city)
                == city.strip().lower()
            )

        if state:
            conditions.append(
                func.lower(InstitutionProfile.state)
                == state.strip().lower()
            )

        today = date.today()

        if admission_open is True:
            conditions.append(
                Course.admission_start.is_not(None)
            )
            conditions.append(
                Course.admission_end.is_not(None)
            )
            conditions.append(
                Course.admission_start <= today
            )
            conditions.append(
                Course.admission_end >= today
            )
        elif admission_open is False:
            conditions.append(
                or_(
                    Course.admission_start.is_(None),
                    Course.admission_end.is_(None),
                    Course.admission_end < today,
                    Course.admission_start > today,
                )
            )

        base_query = (
            select(Course)
            .join(
                InstitutionProfile,
                InstitutionProfile.id
                == Course.institution_profile_id,
            )
            .join(
                Organization,
                Organization.id
                == InstitutionProfile.organization_id,
            )
            .where(*conditions)
        )

        count_query = (
            select(func.count(Course.id))
            .join(
                InstitutionProfile,
                InstitutionProfile.id
                == Course.institution_profile_id,
            )
            .join(
                Organization,
                Organization.id
                == InstitutionProfile.organization_id,
            )
            .where(*conditions)
        )

        total = (await db.execute(count_query)).scalar_one()

        result = await db.execute(
            base_query
            .order_by(
                Course.is_featured.desc(),
                Course.published_at.desc(),
                Course.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        return list(result.scalars().all()), total

    @staticmethod
    def calculate_pages(total: int, page_size: int) -> int:
        if total <= 0:
            return 0

        return math.ceil(total / page_size)
