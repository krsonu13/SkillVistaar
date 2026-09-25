
from __future__ import annotations

from datetime import datetime, timezone

from uuid import UUID

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (

    CREATE_JOB,

    UPDATE_JOB,

    PUBLISH_JOB,

    CLOSE_JOB,

    has_permission,

)

from app.models.job import Job, JobStatus

from app.models.organization import Organization

from app.models.organization_member import OrganizationMember

from app.models.job_skill_requirement import JobSkillRequirement

from app.services.audit_log_service import AuditLogService

MANAGER_ROLES = {

    "ORG_ADMIN",

    "HR",

    "JOB_POSTER",

}

class JobServiceError(Exception):

    pass

class JobNotFoundError(JobServiceError):

    pass

class JobAccessDeniedError(JobServiceError):

    pass

class JobValidationError(JobServiceError):

    pass

class JobService:

    def __init__(self, db: AsyncSession):

        self.db = db

    async def _get_job(self, job_id: UUID) -> Job:

        result = await self.db.execute(

            select(Job).where(Job.id == job_id)

        )

        job = result.scalar_one_or_none()

        if not job:

            raise JobNotFoundError("Job not found.")

        return job

    async def _get_organization(self, organization_id: UUID) -> Organization:

        result = await self.db.execute(

            select(Organization).where(

                Organization.id == organization_id

            )

        )

        organization = result.scalar_one_or_none()

        if not organization:

            raise JobValidationError("Organization not found.")

        if hasattr(organization, "is_active") and not organization.is_active:

            raise JobValidationError("Organization is inactive.")

        return organization

    async def _is_manager(

        self,

        user_id: UUID,

        organization_id: UUID,

    ) -> bool:

        result = await self.db.execute(

            select(OrganizationMember).where(

                OrganizationMember.organization_id == organization_id,

                OrganizationMember.user_id == user_id,

                OrganizationMember.is_active.is_(True),

            )

        )

        members = result.scalars().all()

        return any(

            getattr(member, "role", None) in MANAGER_ROLES

            for member in members

        )

    async def _ensure_manager(

        self,

        user_id: UUID,

        organization_id: UUID,

    ) -> None:

        if not await self._is_manager(

            user_id,

            organization_id,

        ):

            raise JobAccessDeniedError(

                "You are not authorized to manage jobs "

                "for this organization."

            )

    def _ensure_transition(

        self,

        current: str,

        target: str,

    ) -> None:

        allowed = {

            JobStatus.DRAFT.value: {

                JobStatus.PENDING_REVIEW.value,

            },

            JobStatus.PENDING_REVIEW.value: {

                JobStatus.DRAFT.value,

                JobStatus.PUBLISHED.value,

            },

            JobStatus.PUBLISHED.value: {

                JobStatus.PAUSED.value,

                JobStatus.CLOSED.value,

            },

            JobStatus.PAUSED.value: {

                JobStatus.PUBLISHED.value,

                JobStatus.CLOSED.value,

            },

            JobStatus.CLOSED.value: {

                JobStatus.ARCHIVED.value,

            },

            JobStatus.ARCHIVED.value: set(),

        }

        if target not in allowed.get(current, set()):

            raise JobValidationError(

                f"Invalid job status transition: "

                f"{current} -> {target}"

            )

    async def _validate_for_publish(self, job: Job) -> None:

        required_fields = {

            "title": job.title,

            "description": job.description,

            "organization_id": job.organization_id,

            "created_by_user_id": job.created_by_user_id,

            "vacancies": job.vacancies,

            "work_mode": job.work_mode,

        }

        missing = [

            field

            for field, value in required_fields.items()

            if value is None or value == ""

        ]

        if missing:

            raise JobValidationError(

                "Job is incomplete. Missing: "

                + ", ".join(missing)

            )

        if job.vacancies <= 0:

            raise JobValidationError(

                "Vacancies must be greater than zero."

            )

        if (

            job.salary_min is not None

            and job.salary_max is not None

            and job.salary_min > job.salary_max

        ):

            raise JobValidationError(

                "Minimum salary cannot exceed maximum salary."

            )

        now = datetime.now(timezone.utc)

        if job.application_deadline:

            deadline = job.application_deadline

            if deadline.tzinfo is None:

                deadline = deadline.replace(

                    tzinfo=timezone.utc

                )

            if deadline <= now:

                raise JobValidationError(

                    "Application deadline must be in the future."

                )

        result = await self.db.execute(

            select(JobSkillRequirement).where(

                JobSkillRequirement.job_id == job.id

            )

        )

        requirements = result.scalars().all()

        if not requirements:

            raise JobValidationError(

                "At least one skill requirement is required "

                "before publishing."

            )

        required_skills = [

            requirement

            for requirement in requirements

            if requirement.is_required

        ]

        if not required_skills:

            raise JobValidationError(

                "At least one required skill is needed "

                "before publishing."

            )

    async def create_job(

        self,

        *,

        user_id: UUID,

        organization_id: UUID,

        data: dict,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> Job:

        await self._get_organization(organization_id)

        await self._ensure_manager(

            user_id,

            organization_id,

        )

        job = Job(

            organization_id=organization_id,

            created_by_user_id=user_id,

            status=JobStatus.DRAFT.value,

            **data,

        )

        self.db.add(job)

        await self.db.flush()

        await AuditLogService(self.db).record(

            actor_user_id=user_id,

            action="CREATE",

            resource_type="JOB",

            resource_id=job.id,

            description="Created job draft.",

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

        await self.db.commit()

        await self.db.refresh(job)

        return job

    async def get_job(

        self,

        *,

        job_id: UUID,

        user_id: UUID | None = None,

        management_access: bool = False,

    ) -> Job:

        job = await self._get_job(job_id)

        if management_access:

            if user_id is None:

                raise JobAccessDeniedError(

                    "Authenticated user required."

                )

            await self._ensure_manager(

                user_id,

                job.organization_id,

            )

        return job

    async def update_job(

        self,

        *,

        job_id: UUID,

        user_id: UUID,

        data: dict,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> Job:

        job = await self._get_job(job_id)

        await self._ensure_manager(

            user_id,

            job.organization_id,

        )

        if job.status not in {

            JobStatus.DRAFT.value,

            JobStatus.PENDING_REVIEW.value,

        }:

            raise JobValidationError(

                "Only draft or pending-review jobs can be edited."

            )

        protected = {

            "id",

            "organization_id",

            "created_by_user_id",

            "status",

            "published_at",

            "closed_at",

            "created_at",

            "updated_at",

        }

        for key, value in data.items():

            if key not in protected and hasattr(job, key):

                setattr(job, key, value)

        await self.db.flush()

        await AuditLogService(self.db).record(

            actor_user_id=user_id,

            action="UPDATE",

            resource_type="JOB",

            resource_id=job.id,

            description="Updated job.",

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

        await self.db.commit()

        await self.db.refresh(job)

        return job

    async def submit_for_review(

        self,

        *,

        job_id: UUID,

        user_id: UUID,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> Job:

        job = await self._get_job(job_id)

        await self._ensure_manager(

            user_id,

            job.organization_id,

        )

        if job.status != JobStatus.DRAFT.value:

            raise JobValidationError(

                "Only draft jobs can be submitted for review."

            )

        await self._validate_for_publish(job)

        job.status = JobStatus.PENDING_REVIEW.value

        await self.db.flush()

        await AuditLogService(self.db).record(

            actor_user_id=user_id,

            action="UPDATE",

            resource_type="JOB",

            resource_id=job.id,

            description="Submitted job for review.",

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

        await self.db.commit()

        await self.db.refresh(job)

        return job

    async def publish_job(

        self,

        *,

        job_id: UUID,

        user_id: UUID,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> Job:

        job = await self._get_job(job_id)

        await self._ensure_manager(

            user_id,

            job.organization_id,

        )

        if job.status != JobStatus.PENDING_REVIEW.value:

            raise JobValidationError(

                "Only jobs pending review can be published."

            )

        await self._validate_for_publish(job)

        job.status = JobStatus.PUBLISHED.value

        job.published_at = datetime.now(timezone.utc)

        await self.db.flush()

        await AuditLogService(self.db).record(

            actor_user_id=user_id,

            action="APPROVE",

            resource_type="JOB",

            resource_id=job.id,

            description="Published job.",

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

        await self.db.commit()

        await self.db.refresh(job)

        return job

    async def pause_job(

        self,

        *,

        job_id: UUID,

        user_id: UUID,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> Job:

        return await self._change_status(

            job_id=job_id,

            user_id=user_id,

            target=JobStatus.PAUSED.value,

            action="SUSPEND",

            description="Paused job.",

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

    async def resume_job(

        self,

        *,

        job_id: UUID,

        user_id: UUID,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> Job:

        return await self._change_status(

            job_id=job_id,

            user_id=user_id,

            target=JobStatus.PUBLISHED.value,

            action="RESTORE",

            description="Resumed job.",

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

    async def close_job(

        self,

        *,

        job_id: UUID,

        user_id: UUID,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> Job:

        job = await self._change_status(

            job_id=job_id,

            user_id=user_id,

            target=JobStatus.CLOSED.value,

            action="SUSPEND",

            description="Closed job.",

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

        job.closed_at = datetime.now(timezone.utc)

        await self.db.commit()

        await self.db.refresh(job)

        return job

    async def archive_job(

        self,

        *,

        job_id: UUID,

        user_id: UUID,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> Job:

        return await self._change_status(

            job_id=job_id,

            user_id=user_id,

            target=JobStatus.ARCHIVED.value,

            action="UPDATE",

            description="Archived job.",

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

    async def _change_status(

        self,

        *,

        job_id: UUID,

        user_id: UUID,

        target: str,

        action: str,

        description: str,

        ip_address: str | None,

        user_agent: str | None,

        request_id: str | None,

    ) -> Job:

        job = await self._get_job(job_id)

        await self._ensure_manager(

            user_id,

            job.organization_id,

        )

        self._ensure_transition(

            job.status,

            target,

        )

        job.status = target

        await self.db.flush()

        await AuditLogService(self.db).record(

            actor_user_id=user_id,

            action=action,

            resource_type="JOB",

            resource_id=job.id,

            description=description,

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

        await self.db.commit()

        await self.db.refresh(job)

        return job

    async def list_public_jobs(

        self,

        *,

        limit: int = 50,

        offset: int = 0,

    ) -> list[Job]:

        result = await self.db.execute(

            select(Job)

            .join(

                Organization,

                Organization.id == Job.organization_id,

            )

            .where(

                Job.status == JobStatus.PUBLISHED.value,

                Job.is_public.is_(True),

                Organization.is_active.is_(True),

            )

            .order_by(Job.published_at.desc())

            .limit(min(limit, 100))

            .offset(max(offset, 0))

        )

        return list(result.scalars().all())

