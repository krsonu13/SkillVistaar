from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus
from app.models.job_screening_question import (
    JobScreeningQuestion,
    ScreeningQuestionType,
)
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.services.audit_log_service import AuditLogService


MANAGER_ROLES = {
    "ORG_ADMIN",
    "HR",
    "JOB_POSTER",
}


MODIFIABLE_JOB_STATUSES = {
    JobStatus.DRAFT.value,
    JobStatus.PENDING_REVIEW.value,
}


class JobScreeningServiceError(Exception):
    pass


class JobScreeningNotFoundError(JobScreeningServiceError):
    pass


class JobScreeningAccessDeniedError(JobScreeningServiceError):
    pass


class JobScreeningValidationError(JobScreeningServiceError):
    pass


class JobScreeningService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditLogService(db)

    # --------------------------------------------------------
    # Job
    # --------------------------------------------------------

    async def _get_job(self, job_id: UUID) -> Job:
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )

        job = result.scalar_one_or_none()

        if job is None:
            raise JobScreeningNotFoundError(
                "Job not found."
            )

        return job

    async def _get_organization(
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
            raise JobScreeningValidationError(
                "Organization not found."
            )

        return organization

    # --------------------------------------------------------
    # Authorization
    # --------------------------------------------------------

    async def _ensure_job_manager(
        self,
        job: Job,
        user_id: UUID,
    ) -> OrganizationMember:
        organization = await self._get_organization(
            job.organization_id
        )

        if not organization.is_active:
            raise JobScreeningAccessDeniedError(
                "Organization is inactive."
            )

        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id
                == job.organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active.is_(True),
                OrganizationMember.role_code.in_(
                    MANAGER_ROLES
                ),
            )
        )

        member = result.scalar_one_or_none()

        if member is None:
            raise JobScreeningAccessDeniedError(
                "You are not authorized to manage screening questions for this job."
            )

        return member

    async def _ensure_published_job(
        self,
        job: Job,
    ) -> None:
        if job.status != JobStatus.PUBLISHED.value:
            raise JobScreeningAccessDeniedError(
                "Screening questions are available only for published jobs."
            )

        if not job.is_public:
            raise JobScreeningAccessDeniedError(
                "This job is not publicly accepting applications."
            )

        organization = await self._get_organization(
            job.organization_id
        )

        if not organization.is_active:
            raise JobScreeningAccessDeniedError(
                "Organization is inactive."
            )

    # --------------------------------------------------------
    # Question validation
    # --------------------------------------------------------

    @staticmethod
    def _normalize_type(
        question_type: str,
    ) -> str:
        return (
            question_type.value
            if hasattr(question_type, "value")
            else question_type
        )

    @classmethod
    def _validate_question(
        cls,
        question_type: str,
        options: list[str] | None,
    ) -> list[str] | None:
        normalized_type = cls._normalize_type(
            question_type
        )

        valid_types = {
            ScreeningQuestionType.SINGLE_CHOICE.value,
            ScreeningQuestionType.YES_NO.value,
            ScreeningQuestionType.NUMBER.value,
            ScreeningQuestionType.TEXT.value,
        }

        if normalized_type not in valid_types:
            raise JobScreeningValidationError(
                f"Unsupported screening question type: "
                f"{normalized_type}."
            )

        if normalized_type == (
            ScreeningQuestionType.SINGLE_CHOICE.value
        ):
            if not options:
                raise JobScreeningValidationError(
                    "Single-choice questions require at least two options."
                )

            cleaned = [
                option.strip()
                for option in options
                if option and option.strip()
            ]

            if len(cleaned) < 2:
                raise JobScreeningValidationError(
                    "Single-choice questions require at least two non-empty options."
                )

            if len(set(cleaned)) != len(cleaned):
                raise JobScreeningValidationError(
                    "Question options must be unique."
                )

            return cleaned

        if normalized_type in {
            ScreeningQuestionType.YES_NO.value,
            ScreeningQuestionType.NUMBER.value,
            ScreeningQuestionType.TEXT.value,
        }:
            if options:
                raise JobScreeningValidationError(
                    f"{normalized_type} questions cannot define options."
                )

            return None

        return None

    # --------------------------------------------------------
    # List
    # --------------------------------------------------------

    async def list_questions(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        management_access: bool = True,
    ) -> list[JobScreeningQuestion]:
        job = await self._get_job(job_id)

        if management_access:
            await self._ensure_job_manager(
                job,
                user_id,
            )
        else:
            await self._ensure_published_job(job)

        result = await self.db.execute(
            select(JobScreeningQuestion)
            .where(
                JobScreeningQuestion.job_id == job_id
            )
            .order_by(
                JobScreeningQuestion.display_order.asc(),
                JobScreeningQuestion.created_at.asc(),
            )
        )

        return list(result.scalars().all())

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    async def create_question(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        question: str,
        question_type: str,
        options: list[str] | None,
        is_required: bool,
        display_order: int,
    ) -> JobScreeningQuestion:
        job = await self._get_job(job_id)

        await self._ensure_job_manager(
            job,
            user_id,
        )

        if job.status not in MODIFIABLE_JOB_STATUSES:
            raise JobScreeningValidationError(
                "Screening questions can only be modified while the job is in draft or pending review."
            )

        question = question.strip()

        if not question:
            raise JobScreeningValidationError(
                "Question cannot be empty."
            )

        if display_order < 0:
            raise JobScreeningValidationError(
                "Display order cannot be negative."
            )

        normalized_options = self._validate_question(
            question_type,
            options,
        )

        normalized_type = self._normalize_type(
            question_type
        )

        screening_question = JobScreeningQuestion(
            job_id=job_id,
            question=question,
            question_type=normalized_type,
            options=normalized_options,
            is_required=is_required,
            display_order=display_order,
        )

        self.db.add(screening_question)

        await self.db.flush()

        await self.audit.record(
            actor_user_id=user_id,
            action="CREATE",
            resource_type="JOB_SCREENING_QUESTION",
            resource_id=screening_question.id,
            description=(
                "Employer created a job screening question."
            ),
        )

        await self.db.commit()
        await self.db.refresh(screening_question)

        return screening_question

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    async def update_question(
        self,
        *,
        job_id: UUID,
        question_id: UUID,
        user_id: UUID,
        question: str | None = None,
        question_type: str | None = None,
        options: list[str] | None = None,
        is_required: bool | None = None,
        display_order: int | None = None,
    ) -> JobScreeningQuestion:
        job = await self._get_job(job_id)

        await self._ensure_job_manager(
            job,
            user_id,
        )

        if job.status not in MODIFIABLE_JOB_STATUSES:
            raise JobScreeningValidationError(
                "Screening questions can only be modified while the job is in draft or pending review."
            )

        result = await self.db.execute(
            select(JobScreeningQuestion).where(
                JobScreeningQuestion.id == question_id,
                JobScreeningQuestion.job_id == job_id,
            )
        )

        screening_question = (
            result.scalar_one_or_none()
        )

        if screening_question is None:
            raise JobScreeningNotFoundError(
                "Screening question not found."
            )

        final_type = (
            question_type
            if question_type is not None
            else screening_question.question_type
        )

        final_options = (
            options
            if options is not None
            else screening_question.options
        )

        normalized_options = self._validate_question(
            final_type,
            final_options,
        )

        if question is not None:
            cleaned_question = question.strip()

            if not cleaned_question:
                raise JobScreeningValidationError(
                    "Question cannot be empty."
                )

            screening_question.question = (
                cleaned_question
            )

        if question_type is not None:
            screening_question.question_type = (
                self._normalize_type(question_type)
            )

        if options is not None:
            screening_question.options = (
                normalized_options
            )

        if is_required is not None:
            screening_question.is_required = (
                is_required
            )

        if display_order is not None:
            if display_order < 0:
                raise JobScreeningValidationError(
                    "Display order cannot be negative."
                )

            screening_question.display_order = (
                display_order
            )

        await self.audit.record(
            actor_user_id=user_id,
            action="UPDATE",
            resource_type="JOB_SCREENING_QUESTION",
            resource_id=screening_question.id,
            description=(
                "Employer updated a job screening question."
            ),
        )

        await self.db.commit()
        await self.db.refresh(
            screening_question
        )

        return screening_question

    # --------------------------------------------------------
    # Delete
    # --------------------------------------------------------

    async def delete_question(
        self,
        *,
        job_id: UUID,
        question_id: UUID,
        user_id: UUID,
    ) -> None:
        job = await self._get_job(job_id)

        await self._ensure_job_manager(
            job,
            user_id,
        )

        if job.status not in MODIFIABLE_JOB_STATUSES:
            raise JobScreeningValidationError(
                "Screening questions can only be modified while the job is in draft or pending review."
            )

        result = await self.db.execute(
            select(JobScreeningQuestion).where(
                JobScreeningQuestion.id == question_id,
                JobScreeningQuestion.job_id == job_id,
            )
        )

        screening_question = (
            result.scalar_one_or_none()
        )

        if screening_question is None:
            raise JobScreeningNotFoundError(
                "Screening question not found."
            )

        await self.audit.record(
            actor_user_id=user_id,
            action="DELETE",
            resource_type="JOB_SCREENING_QUESTION",
            resource_id=screening_question.id,
            description=(
                "Employer deleted a job screening question."
            ),
        )

        await self.db.delete(
            screening_question
        )

        await self.db.commit()
