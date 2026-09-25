from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import (
    Assessment,
    AssessmentStatus,
)
from app.models.organization import (
    Organization,
    OrganizationVerificationStatus,
)
from app.models.organization_member import (
    OrganizationMember,
    OrganizationMemberRole,
)
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentUpdate,
)


MANAGER_ROLES = {
    OrganizationMemberRole.ORG_ADMIN.value,
    OrganizationMemberRole.HR.value,
    OrganizationMemberRole.ASSESSMENT_MANAGER.value,
}


class AssessmentServiceError(Exception):
    """Base assessment service error."""


class AssessmentNotFoundError(AssessmentServiceError):
    """Assessment does not exist."""


class AssessmentAccessDeniedError(AssessmentServiceError):
    """User does not have assessment access."""


class AssessmentValidationError(AssessmentServiceError):
    """Assessment validation failed."""


class AssessmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # BASIC LOOKUPS
    # ------------------------------------------------------------------

    async def get_assessment(
        self,
        assessment_id: UUID,
    ) -> Assessment:
        result = await self.db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id
            )
        )

        assessment = result.scalar_one_or_none()

        if assessment is None:
            raise AssessmentNotFoundError(
                "Assessment not found."
            )

        return assessment

    async def get_organization(
        self,
        organization_id: UUID,
    ) -> Organization:
        result = await self.db.execute(
            select(Organization).where(
                Organization.id == organization_id
            )
        )

        organization = result.scalar_one_or_none()

        if organization is None:
            raise AssessmentValidationError(
                "Organization not found."
            )

        return organization

    # ------------------------------------------------------------------
    # EMPLOYER ACCESS
    # ------------------------------------------------------------------

    async def ensure_manager_access(
        self,
        user: User,
        organization_id: UUID,
    ) -> Organization:
        organization = await self.get_organization(
            organization_id
        )

        if (
            organization.organization_type != "EMPLOYER"
        ):
            raise AssessmentAccessDeniedError(
                "Assessments can only be managed by employer organizations."
            )

        if (
            organization.verification_status
            != OrganizationVerificationStatus.APPROVED.value
        ):
            raise AssessmentAccessDeniedError(
                "The employer organization must be approved."
            )

        if not organization.is_active:
            raise AssessmentAccessDeniedError(
                "The employer organization is inactive."
            )

        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id
                == organization_id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active.is_(True),
                OrganizationMember.role_code.in_(
                    MANAGER_ROLES
                ),
            )
        )

        membership = result.scalar_one_or_none()

        if membership is None:
            raise AssessmentAccessDeniedError(
                "You do not have permission to manage assessments for this organization."
            )

        return organization

    async def ensure_assessment_access(
        self,
        user: User,
        assessment: Assessment,
    ) -> Organization:
        return await self.ensure_manager_access(
            user=user,
            organization_id=assessment.organization_id,
        )

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    @staticmethod
    def validate_assessment_data(
        data: AssessmentCreate | AssessmentUpdate,
    ) -> None:
        values = data.model_dump(
            exclude_unset=True
        )

        duration = values.get(
            "duration_minutes"
        )

        if duration is not None and duration <= 0:
            raise AssessmentValidationError(
                "Assessment duration must be greater than zero."
            )

        total_marks = values.get(
            "total_marks"
        )

        if total_marks is not None and total_marks < 0:
            raise AssessmentValidationError(
                "Total marks cannot be negative."
            )

        passing_percentage = values.get(
            "passing_percentage"
        )

        if passing_percentage is not None and not (
            0 <= passing_percentage <= 100
        ):
            raise AssessmentValidationError(
                "Passing percentage must be between 0 and 100."
            )

        max_attempts = values.get(
            "max_attempts"
        )

        if max_attempts is not None and max_attempts <= 0:
            raise AssessmentValidationError(
                "Maximum attempts must be greater than zero."
            )

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create_assessment(
        self,
        user: User,
        data: AssessmentCreate,
    ) -> Assessment:
        self.validate_assessment_data(data)

        organization = await self.ensure_manager_access(
            user=user,
            organization_id=data.organization_id,
        )

        existing_result = await self.db.execute(
            select(Assessment).where(
                Assessment.organization_id
                == organization.id,
                Assessment.title == data.title,
            )
        )

        if existing_result.scalar_one_or_none() is not None:
            raise AssessmentValidationError(
                "An assessment with this title already exists for this organization."
            )

        assessment = Assessment(
            organization_id=organization.id,
            created_by_user_id=user.id,
            title=data.title,
            description=data.description,
            assessment_type=data.assessment_type,
            duration_minutes=data.duration_minutes,
            total_marks=0,
            passing_percentage=data.passing_percentage,
            max_attempts=data.max_attempts,
            randomize_questions=data.randomize_questions,
            show_result_immediately=data.show_result_immediately,
            instructions=data.instructions,
            status=AssessmentStatus.DRAFT.value,
        )

        self.db.add(assessment)

        await self.db.commit()
        await self.db.refresh(assessment)

        return assessment

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update_assessment(
        self,
        user: User,
        assessment_id: UUID,
        data: AssessmentUpdate,
    ) -> Assessment:
        self.validate_assessment_data(data)

        assessment = await self.get_assessment(
            assessment_id
        )

        await self.ensure_assessment_access(
            user=user,
            assessment=assessment,
        )

        if assessment.status == AssessmentStatus.ARCHIVED.value:
            raise AssessmentValidationError(
                "Archived assessments cannot be edited."
            )

        values = data.model_dump(
            exclude_unset=True
        )

        for field, value in values.items():
            if field == "organization_id":
                continue

            if hasattr(assessment, field):
                setattr(
                    assessment,
                    field,
                    value,
                )

        # Any change to a published assessment requires
        # another review before publication.
        if (
            assessment.status
            == AssessmentStatus.PUBLISHED.value
        ):
            assessment.status = (
                AssessmentStatus.PENDING_REVIEW.value
            )
            assessment.published_at = None

        await self.db.commit()
        await self.db.refresh(assessment)

        return assessment

    # ------------------------------------------------------------------
    # SUBMIT FOR REVIEW
    # ------------------------------------------------------------------

    async def submit_for_review(
        self,
        user: User,
        assessment_id: UUID,
    ) -> Assessment:
        assessment = await self.get_assessment(
            assessment_id
        )

        await self.ensure_assessment_access(
            user=user,
            assessment=assessment,
        )

        if assessment.status not in {
            AssessmentStatus.DRAFT.value,
            AssessmentStatus.PENDING_REVIEW.value,
        }:
            raise AssessmentValidationError(
                "Only draft assessments can be submitted for review."
            )

        if assessment.total_marks <= 0:
            raise AssessmentValidationError(
                "Assessment must contain questions before review."
            )

        assessment.status = (
            AssessmentStatus.PENDING_REVIEW.value
        )

        await self.db.commit()
        await self.db.refresh(assessment)

        return assessment

    # ------------------------------------------------------------------
    # PUBLISH
    # ------------------------------------------------------------------

    async def publish_assessment(
        self,
        user: User,
        assessment_id: UUID,
    ) -> Assessment:
        assessment = await self.get_assessment(
            assessment_id
        )

        await self.ensure_assessment_access(
            user=user,
            assessment=assessment,
        )

        if assessment.status != (
            AssessmentStatus.PENDING_REVIEW.value
        ):
            raise AssessmentValidationError(
                "Only assessments pending review can be published."
            )

        if assessment.total_marks <= 0:
            raise AssessmentValidationError(
                "Assessment must contain questions before publication."
            )

        assessment.status = (
            AssessmentStatus.PUBLISHED.value
        )
        assessment.published_at = datetime.now(
            timezone.utc
        )

        await self.db.commit()
        await self.db.refresh(assessment)

        return assessment

    # ------------------------------------------------------------------
    # ARCHIVE
    # ------------------------------------------------------------------

    async def archive_assessment(
        self,
        user: User,
        assessment_id: UUID,
    ) -> Assessment:
        assessment = await self.get_assessment(
            assessment_id
        )

        await self.ensure_assessment_access(
            user=user,
            assessment=assessment,
        )

        if assessment.status == (
            AssessmentStatus.ARCHIVED.value
        ):
            return assessment

        assessment.status = (
            AssessmentStatus.ARCHIVED.value
        )

        await self.db.commit()
        await self.db.refresh(assessment)

        return assessment

    # ------------------------------------------------------------------
    # LIST ORGANIZATION ASSESSMENTS
    # ------------------------------------------------------------------

    async def list_organization_assessments(
        self,
        user: User,
        organization_id: UUID,
        include_archived: bool = False,
    ) -> list[Assessment]:
        await self.ensure_manager_access(
            user=user,
            organization_id=organization_id,
        )

        query = select(Assessment).where(
            Assessment.organization_id
            == organization_id
        )

        if not include_archived:
            query = query.where(
                Assessment.status
                != AssessmentStatus.ARCHIVED.value
            )

        query = query.order_by(
            Assessment.created_at.desc()
        )

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def list_published_assessments(self) -> list[Assessment]:
        query = (
            select(Assessment)
            .where(Assessment.status == AssessmentStatus.PUBLISHED.value)
            .order_by(Assessment.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_published_assessment(
        self,
        assessment_id: UUID,
    ) -> Assessment:
        assessment = await self.get_assessment(
            assessment_id
        )

        if assessment.status != (
            AssessmentStatus.PUBLISHED.value
        ):
            raise AssessmentValidationError(
                "Assessment is not published."
            )

        return assessment