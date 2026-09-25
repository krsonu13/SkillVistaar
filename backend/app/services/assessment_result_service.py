
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment

from app.models.assessment_answer import AssessmentAnswer

from app.models.assessment_attempt import (

    AssessmentAttempt,

    AssessmentAttemptStatus,

)

from app.models.assessment_invitation import AssessmentInvitation

from app.models.assessment_question import AssessmentQuestion

from app.models.candidate_profile import CandidateProfile

from app.models.job import Job

from app.models.job_application import JobApplication

from app.models.organization import (

    Organization,

    OrganizationVerificationStatus,

)

from app.models.organization_member import (

    OrganizationMember,

    OrganizationMemberRole,

)

from app.models.user import User

from app.schemas.assessment_result import (

    AssessmentResultAnswer,

    AssessmentResultQuestion,

    AssessmentResultResponse,

)

EMPLOYER_ROLES = {

    OrganizationMemberRole.ORG_ADMIN.value,

    OrganizationMemberRole.HR.value,

    OrganizationMemberRole.ASSESSMENT_MANAGER.value,

}

SUBMITTED_STATUSES = {

    AssessmentAttemptStatus.SUBMITTED.value,

    AssessmentAttemptStatus.AUTO_SUBMITTED.value,

}

class AssessmentResultServiceError(Exception):

    """Base exception for assessment result operations."""

class AssessmentResultNotFoundError(AssessmentResultServiceError):

    """Requested assessment result was not found."""

class AssessmentResultAccessDeniedError(AssessmentResultServiceError):

    """Current user cannot access the requested result."""

class AssessmentResultValidationError(AssessmentResultServiceError):

    """Assessment result is not available or invalid."""

class AssessmentResultService:

    def __init__(self, db: AsyncSession):

        self.db = db

    # ------------------------------------------------------------------

    # LOOKUPS

    # ------------------------------------------------------------------

    async def get_attempt(

        self,

        attempt_id: UUID,

    ) -> AssessmentAttempt:

        result = await self.db.execute(

            select(AssessmentAttempt).where(

                AssessmentAttempt.id == attempt_id

            )

        )

        attempt = result.scalar_one_or_none()

        if attempt is None:

            raise AssessmentResultNotFoundError(

                "Assessment attempt not found."

            )

        return attempt

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

            raise AssessmentResultNotFoundError(

                "Candidate profile not found."

            )

        return candidate

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

            raise AssessmentResultNotFoundError(

                "Assessment not found."

            )

        return assessment

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

            raise AssessmentResultNotFoundError(

                "Assessment invitation not found."

            )

        return invitation

    async def get_application(

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

            raise AssessmentResultNotFoundError(

                "Job application not found."

            )

        return application

    async def get_job(

        self,

        job_id: UUID,

    ) -> Job:

        result = await self.db.execute(

            select(Job).where(

                Job.id == job_id

            )

        )

        job = result.scalar_one_or_none()

        if job is None:

            raise AssessmentResultNotFoundError(

                "Job not found."

            )

        return job

    # ------------------------------------------------------------------

    # RELATIONSHIP / INTEGRITY SAFETY

    # ------------------------------------------------------------------

    async def ensure_attempt_integrity(

        self,

        attempt: AssessmentAttempt,

    ) -> AssessmentInvitation:

        """

        Verify that the attempt, invitation and assessment belong together.

        This prevents an attempt with inconsistent foreign-key relationships

        from being used to expose results.

        """

        invitation = await self.get_invitation(

            attempt.invitation_id

        )

        if invitation.assessment_id != attempt.assessment_id:

            raise AssessmentResultValidationError(

                "Assessment attempt and invitation do not match."

            )

        if (

            invitation.candidate_profile_id

            != attempt.candidate_profile_id

        ):

            raise AssessmentResultValidationError(

                "Assessment attempt and invitation candidate do not match."

            )

        assessment = await self.get_assessment(

            attempt.assessment_id

        )

        if assessment.organization_id is None:

            raise AssessmentResultValidationError(

                "Assessment organization is invalid."

            )

        application = await self.get_application(

            invitation.job_application_id

        )

        if (

            application.candidate_profile_id

            != attempt.candidate_profile_id

        ):

            raise AssessmentResultValidationError(

                "Assessment application and candidate do not match."

            )

        job = await self.get_job(

            application.job_id

        )

        if job.organization_id != assessment.organization_id:

            raise AssessmentResultValidationError(

                "Assessment and job organization do not match."

            )

        if application.job_id != job.id:

            raise AssessmentResultValidationError(

                "Assessment application and job relationship is invalid."

            )

        return invitation

    # ------------------------------------------------------------------

    # USER SAFETY

    # ------------------------------------------------------------------

    @staticmethod

    def ensure_user_active(

        user: User,

    ) -> None:

        if not user.is_active or user.is_suspended:

            raise AssessmentResultAccessDeniedError(

                "Your account is not active."

            )

    # ------------------------------------------------------------------

    # CANDIDATE ACCESS

    # ------------------------------------------------------------------

    async def ensure_candidate_access(

        self,

        user: User,

        attempt: AssessmentAttempt,

    ) -> CandidateProfile:

        self.ensure_user_active(user)

        candidate = await self.get_candidate_profile(

            attempt.candidate_profile_id

        )

        if candidate.user_id != user.id:

            raise AssessmentResultAccessDeniedError(

                "You can only access your own assessment results."

            )

        if candidate.status != "ACTIVE":

            raise AssessmentResultAccessDeniedError(

                "Candidate account is not active."

            )

        return candidate

    # ------------------------------------------------------------------

    # EMPLOYER ACCESS

    # ------------------------------------------------------------------

    async def ensure_employer_access(

        self,

        user: User,

        organization_id: UUID,

    ) -> Organization:

        self.ensure_user_active(user)

        result = await self.db.execute(

            select(Organization).where(

                Organization.id == organization_id

            )

        )

        organization = result.scalar_one_or_none()

        if organization is None:

            raise AssessmentResultNotFoundError(

                "Organization not found."

            )

        if not organization.is_active:

            raise AssessmentResultAccessDeniedError(

                "Organization is inactive."

            )

        if (

            organization.verification_status

            != OrganizationVerificationStatus.APPROVED.value

        ):

            raise AssessmentResultAccessDeniedError(

                "Organization is not verified."

            )

        member_result = await self.db.execute(

            select(OrganizationMember).where(

                OrganizationMember.organization_id

                == organization_id,

                OrganizationMember.user_id == user.id,

                OrganizationMember.is_active.is_(True),

                OrganizationMember.role_code.in_(

                    EMPLOYER_ROLES

                ),

            )

        )

        member = member_result.scalar_one_or_none()

        if member is None:

            raise AssessmentResultAccessDeniedError(

                "You do not have permission to view assessment results "

                "for this organization."

            )

        return organization

    async def ensure_employer_attempt_access(

        self,

        user: User,

        attempt: AssessmentAttempt,

    ) -> Assessment:

        assessment = await self.get_assessment(

            attempt.assessment_id

        )

        await self.ensure_employer_access(

            user=user,

            organization_id=assessment.organization_id,

        )

        await self.ensure_attempt_integrity(

            attempt

        )

        return assessment

    # ------------------------------------------------------------------

    # RESULT SAFETY

    # ------------------------------------------------------------------

    @staticmethod

    def ensure_result_available(

        attempt: AssessmentAttempt,

    ) -> None:

        if attempt.status not in SUBMITTED_STATUSES:

            raise AssessmentResultValidationError(

                "Assessment result is available only after submission."

            )

        if attempt.submitted_at is None:

            raise AssessmentResultValidationError(

                "Assessment result is incomplete."

            )

    @staticmethod

    def ensure_detailed_result_available(

        assessment: Assessment,

    ) -> None:

        if not assessment.show_result_immediately:

            raise AssessmentResultAccessDeniedError(

                "Detailed assessment results are not available for "

                "this assessment."

            )

    # ------------------------------------------------------------------

    # RESPONSE MAPPING

    # ------------------------------------------------------------------

    @staticmethod

    def to_response(

        attempt: AssessmentAttempt,

    ) -> AssessmentResultResponse:

        return AssessmentResultResponse(

            attempt_id=attempt.id,

            invitation_id=attempt.invitation_id,

            assessment_id=attempt.assessment_id,

            candidate_profile_id=attempt.candidate_profile_id,

            attempt_number=attempt.attempt_number,

            status=attempt.status,

            total_questions=attempt.total_questions,

            answered_questions=attempt.answered_questions,

            correct_answers=attempt.correct_answers,

            wrong_answers=attempt.wrong_answers,

            unanswered_questions=attempt.unanswered_questions,

            total_marks=attempt.total_marks,

            obtained_marks=attempt.obtained_marks,

            percentage=attempt.percentage,

            passed=attempt.passed,

            started_at=attempt.started_at,

            submitted_at=attempt.submitted_at,

            expires_at=attempt.expires_at,

        )

    @staticmethod

    def answer_to_response(

        answer: AssessmentAnswer,

    ) -> AssessmentResultAnswer:

        return AssessmentResultAnswer(

            id=answer.id,

            attempt_id=answer.attempt_id,

            question_id=answer.question_id,

            answer_text=answer.answer_text,

            is_answered=answer.is_answered,

            is_correct=answer.is_correct,

            marks_awarded=answer.marks_awarded,

            answered_at=answer.answered_at,

            evaluated_at=answer.evaluated_at,

            created_at=answer.created_at,

            updated_at=answer.updated_at,

        )

    @staticmethod

    def question_to_response(

        question: AssessmentQuestion,

    ) -> AssessmentResultQuestion:

        """

        Candidate-safe question response.

        correct_answer is deliberately never returned.

        """

        return AssessmentResultQuestion(

            id=question.id,

            question_text=question.question_text,

            question_type=question.question_type,

            options=question.options,

            marks=question.marks,

            negative_marks=question.negative_marks,

            skill_id=question.skill_id,

            sequence_number=question.sequence_number,

        )

    # ------------------------------------------------------------------

    # ONE RESULT

    # ------------------------------------------------------------------

    async def get_candidate_result(

        self,

        user: User,

        attempt_id: UUID,

    ) -> AssessmentResultResponse:

        attempt = await self.get_attempt(

            attempt_id

        )

        await self.ensure_candidate_access(

            user=user,

            attempt=attempt,

        )

        await self.ensure_attempt_integrity(

            attempt

        )

        self.ensure_result_available(

            attempt

        )

        return self.to_response(attempt)

    async def get_employer_result(

        self,

        user: User,

        attempt_id: UUID,

    ) -> AssessmentResultResponse:

        attempt = await self.get_attempt(

            attempt_id

        )

        await self.ensure_employer_attempt_access(

            user=user,

            attempt=attempt,

        )

        self.ensure_result_available(

            attempt

        )

        return self.to_response(attempt)

    # ------------------------------------------------------------------

    # CANDIDATE DETAILED RESULT

    # ------------------------------------------------------------------

    async def get_result_questions(

        self,

        user: User,

        attempt_id: UUID,

    ) -> list[AssessmentResultQuestion]:

        attempt = await self.get_attempt(

            attempt_id

        )

        await self.ensure_candidate_access(

            user=user,

            attempt=attempt,

        )

        await self.ensure_attempt_integrity(

            attempt

        )

        self.ensure_result_available(

            attempt

        )

        assessment = await self.get_assessment(

            attempt.assessment_id

        )

        self.ensure_detailed_result_available(

            assessment

        )

        result = await self.db.execute(

            select(AssessmentQuestion)

            .where(

                AssessmentQuestion.assessment_id

                == attempt.assessment_id,

                AssessmentQuestion.is_active.is_(True),

            )

            .order_by(

                AssessmentQuestion.sequence_number.asc()

            )

        )

        questions = list(

            result.scalars().all()

        )

        return [

            self.question_to_response(question)

            for question in questions

        ]

    async def get_candidate_result_answers(

        self,

        user: User,

        attempt_id: UUID,

    ) -> list[AssessmentResultAnswer]:

        attempt = await self.get_attempt(

            attempt_id

        )

        await self.ensure_candidate_access(

            user=user,

            attempt=attempt,

        )

        await self.ensure_attempt_integrity(

            attempt

        )

        self.ensure_result_available(

            attempt

        )

        assessment = await self.get_assessment(

            attempt.assessment_id

        )

        self.ensure_detailed_result_available(

            assessment

        )

        result = await self.db.execute(

            select(AssessmentAnswer)

            .where(

                AssessmentAnswer.attempt_id == attempt_id

            )

            .order_by(

                AssessmentAnswer.created_at.asc()

            )

        )

        answers = list(

            result.scalars().all()

        )

        return [

            self.answer_to_response(answer)

            for answer in answers

        ]

    # ------------------------------------------------------------------

    # EMPLOYER ANSWERS

    # ------------------------------------------------------------------

    async def get_employer_result_answers(

        self,

        user: User,

        attempt_id: UUID,

    ) -> list[AssessmentResultAnswer]:

        attempt = await self.get_attempt(

            attempt_id

        )

        assessment = await self.ensure_employer_attempt_access(

            user=user,

            attempt=attempt,

        )

        self.ensure_result_available(

            attempt

        )

        result = await self.db.execute(

            select(AssessmentAnswer)

            .where(

                AssessmentAnswer.attempt_id == attempt_id

            )

            .order_by(

                AssessmentAnswer.created_at.asc()

            )

        )

        answers = list(

            result.scalars().all()

        )

        return [

            self.answer_to_response(answer)

            for answer in answers

        ]

    # ------------------------------------------------------------------

    # CANDIDATE RESULTS

    # ------------------------------------------------------------------

    async def get_candidate_results(

        self,

        user: User,

    ) -> list[AssessmentResultResponse]:

        self.ensure_user_active(user)

        result = await self.db.execute(

            select(AssessmentAttempt)

            .join(

                CandidateProfile,

                CandidateProfile.id

                == AssessmentAttempt.candidate_profile_id,

            )

            .where(

                CandidateProfile.user_id == user.id,

                CandidateProfile.status == "ACTIVE",

                AssessmentAttempt.status.in_(

                    SUBMITTED_STATUSES

                ),

                AssessmentAttempt.submitted_at.is_not(None),

            )

            .order_by(

                AssessmentAttempt.submitted_at.desc()

            )

        )

        attempts = list(

            result.scalars().all()

        )

        return [

            self.to_response(attempt)

            for attempt in attempts

        ]

    # ------------------------------------------------------------------

    # EMPLOYER RESULTS

    # ------------------------------------------------------------------

    async def get_employer_results(

        self,

        user: User,

        assessment_id: UUID | None = None,

    ) -> list[AssessmentResultResponse]:

        self.ensure_user_active(user)

        if assessment_id is not None:

            assessment = await self.get_assessment(

                assessment_id

            )

            await self.ensure_employer_access(

                user=user,

                organization_id=assessment.organization_id,

            )

            query = (

                select(AssessmentAttempt)

                .where(

                    AssessmentAttempt.assessment_id

                    == assessment_id,

                    AssessmentAttempt.status.in_(

                        SUBMITTED_STATUSES

                    ),

                    AssessmentAttempt.submitted_at.is_not(None),

                )

                .order_by(

                    AssessmentAttempt.submitted_at.desc()

                )

            )

        else:

            organization_ids_result = await self.db.execute(

                select(

                    OrganizationMember.organization_id

                ).where(

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

                raise AssessmentResultAccessDeniedError(

                    "You do not have permission to view assessment results."

                )

            query = (

                select(AssessmentAttempt)

                .join(

                    Assessment,

                    Assessment.id

                    == AssessmentAttempt.assessment_id,

                )

                .join(

                    Organization,

                    Organization.id

                    == Assessment.organization_id,

                )

                .where(

                    Assessment.organization_id.in_(

                        organization_ids

                    ),

                    Organization.is_active.is_(True),

                    Organization.verification_status

                    == OrganizationVerificationStatus.APPROVED.value,

                    AssessmentAttempt.status.in_(

                        SUBMITTED_STATUSES

                    ),

                    AssessmentAttempt.submitted_at.is_not(None),

                )

                .order_by(

                    AssessmentAttempt.submitted_at.desc()

                )

            )

        result = await self.db.execute(query)

        attempts = list(

            result.scalars().all()

        )

        return [

            self.to_response(attempt)

            for attempt in attempts

        ]

