
from __future__ import annotations

from datetime import datetime, timezone

from uuid import UUID

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus

from app.models.assessment_invitation import (

    AssessmentInvitation,

    AssessmentInvitationStatus,

)

from app.models.candidate_profile import CandidateProfile

from app.models.job import Job

from app.models.job_application import (

    ApplicationStatus,

    JobApplication,

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

from app.schemas.assessment_invitation import (

    AssessmentInvitationCreate,

    AssessmentInvitationStatusUpdate,

)

from app.services.audit_log_service import AuditLogService

EMPLOYER_ROLES = {

    OrganizationMemberRole.ORG_ADMIN.value,

    OrganizationMemberRole.HR.value,

    OrganizationMemberRole.ASSESSMENT_MANAGER.value,

}

ALLOWED_STATUS_TRANSITIONS = {

    AssessmentInvitationStatus.INVITED.value: {

        AssessmentInvitationStatus.STARTED.value,

        AssessmentInvitationStatus.CANCELLED.value,

        AssessmentInvitationStatus.EXPIRED.value,

    },

    AssessmentInvitationStatus.STARTED.value: {

        AssessmentInvitationStatus.COMPLETED.value,

        AssessmentInvitationStatus.EXPIRED.value,

    },

    AssessmentInvitationStatus.COMPLETED.value: set(),

    AssessmentInvitationStatus.EXPIRED.value: set(),

    AssessmentInvitationStatus.CANCELLED.value: set(),

}

class AssessmentInvitationServiceError(Exception):

    """Base exception for assessment invitation errors."""

class AssessmentInvitationNotFoundError(

    AssessmentInvitationServiceError

):

    """Invitation does not exist."""

class AssessmentInvitationAccessDeniedError(

    AssessmentInvitationServiceError

):

    """User cannot access the invitation."""

class AssessmentInvitationValidationError(

    AssessmentInvitationServiceError

):

    """Invitation validation failed."""

class AssessmentInvitationService:

    def __init__(self, db: AsyncSession):

        self.db = db

        self.audit = AuditLogService(db)

    # ------------------------------------------------------------------

    # LOOKUPS

    # ------------------------------------------------------------------

    async def get_invitation(

        self,

        invitation_id: UUID,

    ) -> AssessmentInvitation:

        result = await self.db.execute(

            select(AssessmentInvitation).where(

                AssessmentInvitation.id == invitation_id

            )

        )

        invitation = result.scalar_one_or_none()

        if invitation is None:

            raise AssessmentInvitationNotFoundError(

                "Assessment invitation not found."

            )

        return invitation

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

            raise AssessmentInvitationValidationError(

                "Assessment not found."

            )

        return assessment

    async def get_job_application(

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

            raise AssessmentInvitationValidationError(

                "Job application not found."

            )

        return application

    async def get_candidate_profile(

        self,

        candidate_profile_id: UUID,

    ) -> CandidateProfile:

        result = await self.db.execute(

            select(CandidateProfile).where(

                CandidateProfile.id == candidate_profile_id

            )

        )

        candidate = result.scalar_one_or_none()

        if candidate is None:

            raise AssessmentInvitationValidationError(

                "Candidate profile not found."

            )

        return candidate

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

            raise AssessmentInvitationValidationError(

                "Organization not found."

            )

        return organization

    # ------------------------------------------------------------------

    # EMPLOYER ACCESS

    # ------------------------------------------------------------------

    async def ensure_employer_access(

        self,

        user: User,

        organization_id: UUID,

    ) -> Organization:

        organization = await self.get_organization(

            organization_id

        )

        if (

            organization.verification_status

            != OrganizationVerificationStatus.APPROVED.value

            or not organization.is_active

        ):

            raise AssessmentInvitationAccessDeniedError(

                "The organization must be approved and active."

            )

        result = await self.db.execute(

            select(OrganizationMember).where(

                OrganizationMember.organization_id

                == organization_id,

                OrganizationMember.user_id == user.id,

                OrganizationMember.is_active.is_(True),

                OrganizationMember.role_code.in_(EMPLOYER_ROLES),

            )

        )

        membership = result.scalar_one_or_none()

        if membership is None:

            raise AssessmentInvitationAccessDeniedError(

                "You do not have permission to manage assessment invitations."

            )

        return organization

    # ------------------------------------------------------------------

    # VALIDATION

    # ------------------------------------------------------------------

    async def validate_invitation_data(

        self,

        data: AssessmentInvitationCreate,

    ) -> tuple[

        Assessment,

        JobApplication,

        CandidateProfile,

        Job,

    ]:

        assessment = await self.get_assessment(

            data.assessment_id

        )

        application = await self.get_job_application(

            data.job_application_id

        )

        candidate = await self.get_candidate_profile(

            application.candidate_profile_id

        )

        job_result = await self.db.execute(

            select(Job).where(

                Job.id == application.job_id

            )

        )

        job = job_result.scalar_one_or_none()

        if job is None:

            raise AssessmentInvitationValidationError(

                "The job associated with this application was not found."

            )

        # Assessment and job must belong to the same employer.

        if assessment.organization_id != job.organization_id:

            raise AssessmentInvitationValidationError(

                "The assessment and job application must belong to the same organization."

            )

        # The application itself must belong to this job.

        if application.job_id != job.id:

            raise AssessmentInvitationValidationError(

                "The application is not associated with the selected job."

            )

        # Candidate must match the application.

        if application.candidate_profile_id != candidate.id:

            raise AssessmentInvitationValidationError(

                "The application candidate does not match the candidate profile."

            )

        # Assessment must already be published.

        if assessment.status != AssessmentStatus.PUBLISHED.value:

            raise AssessmentInvitationValidationError(

                "Only published assessments can be invited."

            )

        # A candidate must be shortlisted before assessment.

        if application.status != ApplicationStatus.SHORTLISTED.value:

            raise AssessmentInvitationValidationError(

                "Only shortlisted candidates can receive assessment invitations."

            )

        # Job must still be usable.

        if job.status != "PUBLISHED":

            raise AssessmentInvitationValidationError(

                "The associated job is no longer accepting recruitment actions."

            )

        if not job.is_public:

            raise AssessmentInvitationValidationError(

                "The associated job is not publicly active."

            )

        if data.expires_at is not None:

            now = datetime.now(timezone.utc)

            expires_at = data.expires_at

            if expires_at.tzinfo is None:

                expires_at = expires_at.replace(

                    tzinfo=timezone.utc

                )

            if expires_at <= now:

                raise AssessmentInvitationValidationError(

                    "Invitation expiry must be in the future."

                )

        return assessment, application, candidate, job

    # ------------------------------------------------------------------

    # CREATE

    # ------------------------------------------------------------------

    async def create_invitation(

        self,

        user: User,

        data: AssessmentInvitationCreate,

        *,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> AssessmentInvitation:

        (

            assessment,

            application,

            candidate,

            job,

        ) = await self.validate_invitation_data(data)

        await self.ensure_employer_access(

            user=user,

            organization_id=assessment.organization_id,

        )

        existing_result = await self.db.execute(

            select(AssessmentInvitation).where(

                AssessmentInvitation.assessment_id

                == assessment.id,

                AssessmentInvitation.job_application_id

                == application.id,

                AssessmentInvitation.is_active.is_(True),

            )

        )

        existing = existing_result.scalar_one_or_none()

        if existing is not None:

            if existing.status in {

                AssessmentInvitationStatus.INVITED.value,

                AssessmentInvitationStatus.STARTED.value,

            }:

                raise AssessmentInvitationValidationError(

                    "An active invitation already exists for this application."

                )

        invitation = AssessmentInvitation(

            assessment_id=assessment.id,

            job_application_id=application.id,

            candidate_profile_id=candidate.id,

            invited_by_user_id=user.id,

            status=AssessmentInvitationStatus.INVITED.value,

            message=data.message,

            expires_at=data.expires_at,

        )

        self.db.add(invitation)

        # Keep the recruitment state machine consistent.

        application.status = (

            ApplicationStatus.ASSESSMENT.value

        )

        await self.db.flush()

        await self.audit.record(

            actor_user_id=user.id,

            action="CREATE",

            resource_type="ASSESSMENT_INVITATION",

            resource_id=invitation.id,

            description=(

                f"Assessment invitation created for job application "

                f"{application.id}."

            ),

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

            metadata={

                "assessment_id": str(assessment.id),

                "job_id": str(job.id),

                "job_application_id": str(application.id),

                "candidate_profile_id": str(candidate.id),

            },

        )

        await self.db.commit()

        await self.db.refresh(invitation)

        return invitation

    # ------------------------------------------------------------------

    # EMPLOYER ACCESS TO ONE INVITATION

    # ------------------------------------------------------------------

    async def ensure_employer_invitation_access(

        self,

        user: User,

        invitation: AssessmentInvitation,

    ) -> None:

        assessment = await self.get_assessment(

            invitation.assessment_id

        )

        await self.ensure_employer_access(

            user=user,

            organization_id=assessment.organization_id,

        )

    # ------------------------------------------------------------------

    # CANDIDATE ACCESS

    # ------------------------------------------------------------------

    async def ensure_candidate_access(

        self,

        user: User,

        invitation: AssessmentInvitation,

    ) -> CandidateProfile:

        candidate = await self.get_candidate_profile(

            invitation.candidate_profile_id

        )

        if candidate.user_id != user.id:

            raise AssessmentInvitationAccessDeniedError(

                "You can only access your own assessment invitations."

            )

        if candidate.status != "ACTIVE":

            raise AssessmentInvitationAccessDeniedError(

                "Candidate account is not active."

            )

        return candidate

    # ------------------------------------------------------------------

    # EXPIRY

    # ------------------------------------------------------------------

    @staticmethod

    def _utc_now() -> datetime:

        return datetime.now(timezone.utc)

    async def expire_if_needed(

        self,

        invitation: AssessmentInvitation,

    ) -> AssessmentInvitation:

        if (

            invitation.expires_at is None

            or invitation.status

            not in {

                AssessmentInvitationStatus.INVITED.value,

                AssessmentInvitationStatus.STARTED.value,

            }

        ):

            return invitation

        expires_at = invitation.expires_at

        if expires_at.tzinfo is None:

            expires_at = expires_at.replace(

                tzinfo=timezone.utc

            )

        if self._utc_now() < expires_at:

            return invitation

        invitation.status = (

            AssessmentInvitationStatus.EXPIRED.value

        )

        invitation.is_active = False

        await self.db.commit()

        await self.db.refresh(invitation)

        return invitation

    # ------------------------------------------------------------------

    # START

    # ------------------------------------------------------------------

    async def start_invitation(

        self,

        user: User,

        invitation_id: UUID,

    ) -> AssessmentInvitation:

        invitation = await self.get_invitation(

            invitation_id

        )

        await self.ensure_candidate_access(

            user=user,

            invitation=invitation,

        )

        invitation = await self.expire_if_needed(

            invitation

        )

        if invitation.status == (

            AssessmentInvitationStatus.STARTED.value

        ):

            return invitation

        if invitation.status != (

            AssessmentInvitationStatus.INVITED.value

        ):

            raise AssessmentInvitationValidationError(

                "This assessment invitation is no longer available."

            )

        if not invitation.is_active:

            raise AssessmentInvitationValidationError(

                "This assessment invitation is inactive."

            )

        assessment = await self.get_assessment(

            invitation.assessment_id

        )

        if assessment.status != AssessmentStatus.PUBLISHED.value:

            raise AssessmentInvitationValidationError(

                "Only published assessments can be attempted."

            )

        now = self._utc_now()

        invitation.status = (

            AssessmentInvitationStatus.STARTED.value

        )

        invitation.started_at = now

        await self.db.commit()

        await self.db.refresh(invitation)

        return invitation

    # ------------------------------------------------------------------

    # CANCEL

    # ------------------------------------------------------------------

    async def cancel_invitation(

        self,

        user: User,

        invitation_id: UUID,

        *,

        ip_address: str | None = None,

        user_agent: str | None = None,

        request_id: str | None = None,

    ) -> AssessmentInvitation:

        invitation = await self.get_invitation(

            invitation_id

        )

        await self.ensure_employer_invitation_access(

            user=user,

            invitation=invitation,

        )

        invitation = await self.expire_if_needed(

            invitation

        )

        if invitation.status not in {

            AssessmentInvitationStatus.INVITED.value,

            AssessmentInvitationStatus.STARTED.value,

        }:

            raise AssessmentInvitationValidationError(

                "Only active invitations can be cancelled."

            )

        invitation.status = (

            AssessmentInvitationStatus.CANCELLED.value

        )

        invitation.is_active = False

        await self.audit.record(

            actor_user_id=user.id,

            action="UPDATE",

            resource_type="ASSESSMENT_INVITATION",

            resource_id=invitation.id,

            description="Assessment invitation cancelled.",

            ip_address=ip_address,

            user_agent=user_agent,

            request_id=request_id,

        )

        await self.db.commit()

        await self.db.refresh(invitation)

        return invitation

    # ------------------------------------------------------------------

    # STATUS UPDATE

    # ------------------------------------------------------------------

    async def update_status(

        self,

        user: User,

        invitation_id: UUID,

        data: AssessmentInvitationStatusUpdate,

    ) -> AssessmentInvitation:

        invitation = await self.get_invitation(

            invitation_id

        )

        invitation = await self.expire_if_needed(

            invitation

        )

        current_status = invitation.status

        requested_status = data.status.upper()

        try:

            AssessmentInvitationStatus(requested_status)

        except ValueError:

            raise AssessmentInvitationValidationError(

                "Invalid assessment invitation status."

            )

        if requested_status == current_status:

            return invitation

        if requested_status not in ALLOWED_STATUS_TRANSITIONS.get(

            current_status,

            set(),

        ):

            raise AssessmentInvitationValidationError(

                f"Cannot change invitation status from "

                f"{current_status} to {requested_status}."

            )

        if requested_status == (

            AssessmentInvitationStatus.STARTED.value

        ):

            await self.ensure_candidate_access(

                user=user,

                invitation=invitation,

            )

        elif requested_status == (

            AssessmentInvitationStatus.COMPLETED.value

        ):

            await self.ensure_candidate_access(

                user=user,

                invitation=invitation,

            )

        else:

            await self.ensure_employer_invitation_access(

                user=user,

                invitation=invitation,

            )

        now = self._utc_now()

        invitation.status = requested_status

        if requested_status == (

            AssessmentInvitationStatus.STARTED.value

        ):

            invitation.started_at = now

        elif requested_status == (

            AssessmentInvitationStatus.COMPLETED.value

        ):

            invitation.completed_at = now

            invitation.is_active = False

        elif requested_status in {

            AssessmentInvitationStatus.CANCELLED.value,

            AssessmentInvitationStatus.EXPIRED.value,

        }:

            invitation.is_active = False

        await self.db.commit()

        await self.db.refresh(invitation)

        return invitation

    # ------------------------------------------------------------------

    # CANDIDATE LIST

    # ------------------------------------------------------------------

    async def get_candidate_invitations(

        self,

        user: User,

    ) -> list[AssessmentInvitation]:

        result = await self.db.execute(

            select(AssessmentInvitation)

            .join(

                CandidateProfile,

                CandidateProfile.id

                == AssessmentInvitation.candidate_profile_id,

            )

            .where(

                CandidateProfile.user_id == user.id,

            )

            .order_by(

                AssessmentInvitation.invited_at.desc()

            )

        )

        invitations = list(result.scalars().all())

        for invitation in invitations:

            await self.expire_if_needed(invitation)

        return invitations

    # ------------------------------------------------------------------

    # EMPLOYER LIST

    # ------------------------------------------------------------------

    async def get_employer_invitations(

        self,

        user: User,

        assessment_id: UUID | None = None,

    ) -> list[AssessmentInvitation]:

        if assessment_id is not None:

            assessment = await self.get_assessment(

                assessment_id

            )

            await self.ensure_employer_access(

                user=user,

                organization_id=assessment.organization_id,

            )

            query = select(AssessmentInvitation).where(

                AssessmentInvitation.assessment_id

                == assessment_id

            )

        else:

            organization_ids_result = await self.db.execute(

                select(OrganizationMember.organization_id).where(

                    OrganizationMember.user_id == user.id,

                    OrganizationMember.is_active.is_(True),

                    OrganizationMember.role_code.in_(

                        EMPLOYER_ROLES

                    ),

                )

            )

            organization_ids = list(

                organization_ids_result.scalars().all()

            )

            if not organization_ids:

                raise AssessmentInvitationAccessDeniedError(

                    "You do not have permission to view assessment invitations."

                )

            query = (

                select(AssessmentInvitation)

                .join(

                    Assessment,

                    Assessment.id

                    == AssessmentInvitation.assessment_id,

                )

                .where(

                    Assessment.organization_id.in_(

                        organization_ids

                    )

                )

            )

        query = query.order_by(

            AssessmentInvitation.invited_at.desc()

        )

        result = await self.db.execute(query)

        invitations = list(result.scalars().all())

        for invitation in invitations:

            await self.expire_if_needed(invitation)

        return invitations

