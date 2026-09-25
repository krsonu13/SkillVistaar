from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application_status_history import ApplicationStatusHistory
from app.models.candidate_profile import (
    CandidateProfile,
    CandidateProfileStatus,
)
from app.models.candidate_skill import (
    CandidateSkill,
    CandidateSkillStatus,
)
from app.models.document import (
    DocumentScanStatus,
    DocumentType,
    PrivateDocument,
)
from app.models.job import Job, JobStatus
from app.models.job_application import (
    ApplicationStatus,
    JobApplication,
)
from app.models.job_skill_requirement import JobSkillRequirement
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.user import User
from app.services.audit_log_service import AuditLogService


class JobApplicationServiceError(Exception):
    pass


class JobApplicationNotFoundError(JobApplicationServiceError):
    pass


class JobApplicationAccessDeniedError(JobApplicationServiceError):
    pass


class JobApplicationValidationError(JobApplicationServiceError):
    pass


MANAGER_ROLES = {
    "ORG_ADMIN",
    "HR",
    "JOB_POSTER",
}


ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    ApplicationStatus.APPLIED.value: {
        ApplicationStatus.UNDER_REVIEW.value,
        ApplicationStatus.SHORTLISTED.value,
        ApplicationStatus.REJECTED.value,
    },
    ApplicationStatus.UNDER_REVIEW.value: {
        ApplicationStatus.SHORTLISTED.value,
        ApplicationStatus.REJECTED.value,
    },
    ApplicationStatus.SHORTLISTED.value: {
        ApplicationStatus.ASSESSMENT.value,
        ApplicationStatus.INTERVIEW.value,
        ApplicationStatus.SELECTED.value,
        ApplicationStatus.REJECTED.value,
    },
    ApplicationStatus.ASSESSMENT.value: {
        ApplicationStatus.INTERVIEW.value,
        ApplicationStatus.SELECTED.value,
        ApplicationStatus.REJECTED.value,
    },
    ApplicationStatus.INTERVIEW.value: {
        ApplicationStatus.SELECTED.value,
        ApplicationStatus.REJECTED.value,
    },
    ApplicationStatus.SELECTED.value: set(),
    ApplicationStatus.REJECTED.value: set(),
    ApplicationStatus.WITHDRAWN.value: set(),
}


class JobApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditLogService(db)

    # --------------------------------------------------------
    # Basic lookups
    # --------------------------------------------------------

    async def _get_job(self, job_id: UUID) -> Job:
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )

        job = result.scalar_one_or_none()

        if job is None:
            raise JobApplicationNotFoundError("Job not found.")

        return job

    async def _get_application(
        self,
        application_id: UUID,
    ) -> JobApplication:
        result = await self.db.execute(
            select(JobApplication).where(
                JobApplication.id == application_id
            )
        )

        application = result.scalar_one_or_none()

        if application is None:
            raise JobApplicationNotFoundError(
                "Job application not found."
            )

        return application

    # --------------------------------------------------------
    # User / candidate validation
    # --------------------------------------------------------

    async def _ensure_candidate(self, user_id: UUID) -> User:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )

        user = result.scalar_one_or_none()

        if user is None:
            raise JobApplicationAccessDeniedError(
                "User account not found."
            )

        if not user.is_active:
            raise JobApplicationAccessDeniedError(
                "Your account is inactive."
            )

        if user.is_suspended:
            raise JobApplicationAccessDeniedError(
                "Your account is suspended."
            )

        return user

    async def _get_candidate_profile(
        self,
        user_id: UUID,
    ) -> CandidateProfile:
        result = await self.db.execute(
            select(CandidateProfile).where(
                CandidateProfile.user_id == user_id
            )
        )

        profile = result.scalar_one_or_none()

        if profile is None:
            raise JobApplicationValidationError(
                "Candidate profile is required before applying for a job."
            )

        if profile.status != CandidateProfileStatus.ACTIVE.value:
            raise JobApplicationValidationError(
                "Your candidate profile is not active."
            )

        return profile

    # --------------------------------------------------------
    # Employer authorization
    # --------------------------------------------------------

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
            raise JobApplicationValidationError(
                "Organization was not found."
            )

        return organization

    async def _ensure_job_manager(
        self,
        job: Job,
        user_id: UUID,
    ) -> OrganizationMember:
        organization = await self._get_organization(
            job.organization_id
        )

        if not organization.is_active:
            raise JobApplicationAccessDeniedError(
                "This organization is inactive."
            )

        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id
                == job.organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active.is_(True),
                OrganizationMember.role_code.in_(MANAGER_ROLES),
            )
        )

        member = result.scalar_one_or_none()

        if member is None:
            raise JobApplicationAccessDeniedError(
                "You are not authorized to manage applications for this organization."
            )

        return member

    # --------------------------------------------------------
    # Job availability
    # --------------------------------------------------------

    @staticmethod
    def _deadline_is_valid(
        deadline: datetime | None,
    ) -> bool:
        if deadline is None:
            return True

        if deadline.tzinfo is None:
            deadline = deadline.replace(
                tzinfo=timezone.utc
            )

        return deadline > datetime.now(timezone.utc)

    async def _ensure_job_accepts_applications(
        self,
        job: Job,
    ) -> None:
        if job.status != JobStatus.PUBLISHED.value:
            raise JobApplicationValidationError(
                "Applications are accepted only for published jobs."
            )

        if not job.is_public:
            raise JobApplicationAccessDeniedError(
                "This job is not publicly accepting applications."
            )

        if not self._deadline_is_valid(
            job.application_deadline
        ):
            raise JobApplicationValidationError(
                "The application deadline has passed."
            )

        organization = await self._get_organization(
            job.organization_id
        )

        if not organization.is_active:
            raise JobApplicationValidationError(
                "The employer organization is not active."
            )

    # --------------------------------------------------------
    # Resume validation
    # --------------------------------------------------------

    async def _validate_resume_document(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> PrivateDocument:
        result = await self.db.execute(
            select(PrivateDocument).where(
                PrivateDocument.id == document_id
            )
        )

        document = result.scalar_one_or_none()

        if document is None:
            raise JobApplicationValidationError(
                "Resume document was not found."
            )

        if document.owner_user_id != user_id:
            raise JobApplicationAccessDeniedError(
                "You can only use your own resume."
            )

        if not document.is_active:
            raise JobApplicationValidationError(
                "The selected resume is inactive."
            )

        if document.document_type != DocumentType.RESUME.value:
            raise JobApplicationValidationError(
                "The selected document is not a resume."
            )

        if document.scan_status != DocumentScanStatus.CLEAN.value:
            raise JobApplicationValidationError(
                "The selected resume has not passed document security scanning."
            )

        return document

    # --------------------------------------------------------
    # Match calculation
    # --------------------------------------------------------

    async def _calculate_match_score(
        self,
        candidate_profile_id: UUID,
        job_id: UUID,
    ) -> tuple[float, int, int, int, int]:
        requirements_result = await self.db.execute(
            select(JobSkillRequirement).where(
                JobSkillRequirement.job_id == job_id
            )
        )

        requirements = list(
            requirements_result.scalars().all()
        )

        if not requirements:
            return 0.0, 0, 0, 0, 0

        skills_result = await self.db.execute(
            select(CandidateSkill).where(
                CandidateSkill.candidate_profile_id
                == candidate_profile_id,
                CandidateSkill.status
                == CandidateSkillStatus.VERIFIED.value,
            )
        )

        candidate_skills = list(
            skills_result.scalars().all()
        )

        verified_skill_ids = {
            skill.skill_id
            for skill in candidate_skills
        }

        required = [
            requirement
            for requirement in requirements
            if requirement.is_required
        ]

        preferred = [
            requirement
            for requirement in requirements
            if not requirement.is_required
        ]

        matched_required = sum(
            1
            for requirement in required
            if requirement.skill_id in verified_skill_ids
        )

        matched_preferred = sum(
            1
            for requirement in preferred
            if requirement.skill_id in verified_skill_ids
        )

        total_weight = (
            len(required) * 2
            + len(preferred)
        )

        weighted_score = (
            (
                matched_required * 2
                + matched_preferred
            )
            / total_weight
            * 100
            if total_weight
            else 0.0
        )

        return (
            round(
                max(0.0, min(100.0, weighted_score)),
                2,
            ),
            matched_required,
            len(required),
            matched_preferred,
            len(preferred),
        )

    # --------------------------------------------------------
    # Create application
    # --------------------------------------------------------

    async def create_application(
        self,
        *,
        job_id: UUID,
        candidate_user_id: UUID,
        cover_letter: str | None,
        resume_document_id: UUID | None,
        consent_to_share_profile: bool,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> JobApplication:
        await self._ensure_candidate(candidate_user_id)

        candidate_profile = await self._get_candidate_profile(
            candidate_user_id
        )

        job = await self._get_job(job_id)

        await self._ensure_job_accepts_applications(job)

        if not consent_to_share_profile:
            raise JobApplicationValidationError(
                "Consent to share your profile with the employer is required."
            )

        if resume_document_id is not None:
            await self._validate_resume_document(
                candidate_user_id,
                resume_document_id,
            )

        duplicate_result = await self.db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job_id,
                JobApplication.candidate_profile_id
                == candidate_profile.id,
            )
        )

        existing = duplicate_result.scalar_one_or_none()

        if existing is not None:
            raise JobApplicationValidationError(
                "You have already applied for this job."
            )

        (
            match_score,
            matched_required,
            total_required,
            matched_preferred,
            total_preferred,
        ) = await self._calculate_match_score(
            candidate_profile.id,
            job_id,
        )

        application = JobApplication(
            job_id=job_id,
            candidate_profile_id=candidate_profile.id,
            candidate_user_id=candidate_user_id,
            status=ApplicationStatus.APPLIED.value,
            cover_letter=cover_letter,
            resume_document_id=resume_document_id,
            match_score=match_score,
            matched_required_skills=matched_required,
            total_required_skills=total_required,
            matched_preferred_skills=matched_preferred,
            total_preferred_skills=total_preferred,
            consent_to_share_profile=True,
        )

        self.db.add(application)

        await self.db.flush()

        history = ApplicationStatusHistory(
            application_id=application.id,
            old_status=None,
            new_status=ApplicationStatus.APPLIED.value,
            changed_by_user_id=candidate_user_id,
            reason="Application submitted.",
        )

        self.db.add(history)

        await self.audit.record(
            actor_user_id=candidate_user_id,
            action="CREATE",
            resource_type="JOB_APPLICATION",
            resource_id=application.id,
            description="Candidate submitted a job application.",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        await self.db.commit()
        await self.db.refresh(application)

        return application

    # --------------------------------------------------------
    # Candidate applications
    # --------------------------------------------------------

    async def list_candidate_applications(
        self,
        candidate_user_id: UUID,
    ) -> list[JobApplication]:
        await self._ensure_candidate(candidate_user_id)

        result = await self.db.execute(
            select(JobApplication)
            .where(
                JobApplication.candidate_user_id
                == candidate_user_id
            )
            .order_by(
                JobApplication.applied_at.desc()
            )
        )

        return list(result.scalars().all())

    async def get_candidate_application(
        self,
        *,
        application_id: UUID,
        candidate_user_id: UUID,
    ) -> JobApplication:
        await self._ensure_candidate(candidate_user_id)

        application = await self._get_application(
            application_id
        )

        if application.candidate_user_id != candidate_user_id:
            raise JobApplicationAccessDeniedError(
                "You can only access your own application."
            )

        return application

    # --------------------------------------------------------
    # Candidate withdrawal
    # --------------------------------------------------------

    async def withdraw_application(
        self,
        *,
        application_id: UUID,
        candidate_user_id: UUID,
        reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> JobApplication:
        await self._ensure_candidate(candidate_user_id)

        application = await self._get_application(
            application_id
        )

        if application.candidate_user_id != candidate_user_id:
            raise JobApplicationAccessDeniedError(
                "You can only withdraw your own application."
            )

        current_status = application.status

        withdrawable_statuses = {
            ApplicationStatus.APPLIED.value,
            ApplicationStatus.UNDER_REVIEW.value,
            ApplicationStatus.SHORTLISTED.value,
            ApplicationStatus.ASSESSMENT.value,
            ApplicationStatus.INTERVIEW.value,
        }

        if current_status not in withdrawable_statuses:
            raise JobApplicationValidationError(
                "This application can no longer be withdrawn."
            )

        application.status = ApplicationStatus.WITHDRAWN.value

        history = ApplicationStatusHistory(
            application_id=application.id,
            old_status=current_status,
            new_status=ApplicationStatus.WITHDRAWN.value,
            changed_by_user_id=candidate_user_id,
            reason=reason or "Candidate withdrew the application.",
        )

        self.db.add(history)

        await self.audit.record(
            actor_user_id=candidate_user_id,
            action="UPDATE",
            resource_type="JOB_APPLICATION",
            resource_id=application.id,
            description=(
                f"Candidate withdrew application from "
                f"{current_status}."
            ),
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        await self.db.commit()
        await self.db.refresh(application)

        return application

    # --------------------------------------------------------
    # Employer applications
    # --------------------------------------------------------

    async def list_job_applications(
        self,
        *,
        job_id: UUID,
        manager_user_id: UUID,
    ) -> list[JobApplication]:
        job = await self._get_job(job_id)

        await self._ensure_job_manager(
            job,
            manager_user_id,
        )

        result = await self.db.execute(
            select(JobApplication)
            .where(
                JobApplication.job_id == job_id
            )
            .order_by(
                JobApplication.match_score.desc(),
                JobApplication.applied_at.asc(),
            )
        )

        return list(result.scalars().all())

    async def get_job_application(
        self,
        *,
        application_id: UUID,
        manager_user_id: UUID,
    ) -> JobApplication:
        application = await self._get_application(
            application_id
        )

        job = await self._get_job(
            application.job_id
        )

        await self._ensure_job_manager(
            job,
            manager_user_id,
        )

        return application

    # --------------------------------------------------------
    # Application status
    # --------------------------------------------------------

    async def update_application_status(
        self,
        *,
        application_id: UUID,
        manager_user_id: UUID,
        new_status: ApplicationStatus,
        reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> JobApplication:
        application = await self._get_application(
            application_id
        )

        job = await self._get_job(
            application.job_id
        )

        await self._ensure_job_manager(
            job,
            manager_user_id,
        )

        current_status = application.status
        target_status = new_status.value

        allowed = ALLOWED_STATUS_TRANSITIONS.get(
            current_status,
            set(),
        )

        if target_status not in allowed:
            raise JobApplicationValidationError(
                f"Invalid application status transition: "
                f"{current_status} → {target_status}."
            )

        if (
            target_status
            == ApplicationStatus.REJECTED.value
            and not reason
        ):
            raise JobApplicationValidationError(
                "A rejection reason is required."
            )

        if (
            target_status
            == ApplicationStatus.SELECTED.value
            and current_status
            not in {
                ApplicationStatus.SHORTLISTED.value,
                ApplicationStatus.ASSESSMENT.value,
                ApplicationStatus.INTERVIEW.value,
            }
        ):
            raise JobApplicationValidationError(
                "A candidate must reach the recruitment shortlist stage before selection."
            )

        application.status = target_status

        history = ApplicationStatusHistory(
            application_id=application.id,
            old_status=current_status,
            new_status=target_status,
            changed_by_user_id=manager_user_id,
            reason=reason,
        )

        self.db.add(history)

        await self.audit.record(
            actor_user_id=manager_user_id,
            action="UPDATE",
            resource_type="JOB_APPLICATION",
            resource_id=application.id,
            description=(
                f"Application status changed from "
                f"{current_status} to {target_status}."
            ),
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        await self.db.commit()
        await self.db.refresh(application)

        return application
