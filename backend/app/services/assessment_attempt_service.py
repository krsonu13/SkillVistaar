
from __future__ import annotations

import random

from datetime import datetime, timedelta, timezone

from uuid import UUID

from sqlalchemy import func, select

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment

from app.models.assessment_answer import AssessmentAnswer

from app.models.assessment_attempt import (

    AssessmentAttempt,

    AssessmentAttemptStatus,

)

from app.models.assessment_invitation import (

    AssessmentInvitation,

    AssessmentInvitationStatus,

)

from app.models.assessment_question import (

    AssessmentQuestion,

    AssessmentQuestionType,

)

from app.models.candidate_profile import CandidateProfile

from app.models.job_application import (

    ApplicationStatus,

    JobApplication,

)

from app.models.user import User

from app.schemas.assessment_attempt import AssessmentAttemptCreate

class AssessmentAttemptServiceError(Exception):

    """Base assessment attempt error."""

class AssessmentAttemptNotFoundError(AssessmentAttemptServiceError):

    """Attempt was not found."""

class AssessmentAttemptAccessDeniedError(AssessmentAttemptServiceError):

    """User cannot access the attempt."""

class AssessmentAttemptValidationError(AssessmentAttemptServiceError):

    """Invalid assessment attempt operation."""

class AssessmentAttemptService:

    def __init__(self, db: AsyncSession):

        self.db = db

    # ------------------------------------------------------------------

    # BASIC LOOKUPS

    # ------------------------------------------------------------------

    async def get_attempt(self, attempt_id: UUID) -> AssessmentAttempt:

        result = await self.db.execute(

            select(AssessmentAttempt).where(

                AssessmentAttempt.id == attempt_id

            )

        )

        attempt = result.scalar_one_or_none()

        if attempt is None:

            raise AssessmentAttemptNotFoundError(

                "Assessment attempt not found."

            )

        return attempt

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

            raise AssessmentAttemptValidationError(

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

            raise AssessmentAttemptValidationError(

                "Assessment not found."

            )

        return assessment

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

            raise AssessmentAttemptValidationError(

                "Candidate profile not found."

            )

        return candidate

    async def get_question(

        self,

        question_id: UUID,

    ) -> AssessmentQuestion:

        result = await self.db.execute(

            select(AssessmentQuestion).where(

                AssessmentQuestion.id == question_id,

                AssessmentQuestion.is_active.is_(True),

            )

        )

        question = result.scalar_one_or_none()

        if question is None:

            raise AssessmentAttemptValidationError(

                "Assessment question not found."

            )

        return question

    async def _get_attempt_questions(

        self,

        attempt: AssessmentAttempt,

    ) -> list[AssessmentQuestion]:

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

        return list(result.scalars().all())

    async def _validate_attempt_integrity(

        self,

        attempt: AssessmentAttempt,

    ) -> AssessmentInvitation:

        invitation = await self.get_invitation(

            attempt.invitation_id

        )

        if invitation.assessment_id != attempt.assessment_id:

            raise AssessmentAttemptValidationError(

                "Assessment attempt does not match its invitation."

            )

        if invitation.candidate_profile_id != attempt.candidate_profile_id:

            raise AssessmentAttemptValidationError(

                "Assessment attempt candidate does not match its invitation."

            )

        return invitation

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

            raise AssessmentAttemptAccessDeniedError(

                "You can only access your own assessment attempt."

            )

        if candidate.status != "ACTIVE":

            raise AssessmentAttemptAccessDeniedError(

                "Candidate profile is not active."

            )

        return candidate

    async def ensure_attempt_candidate_access(

        self,

        user: User,

        attempt: AssessmentAttempt,

    ) -> CandidateProfile:

        candidate = await self.get_candidate_profile(

            attempt.candidate_profile_id

        )

        if candidate.user_id != user.id:

            raise AssessmentAttemptAccessDeniedError(

                "You can only access your own assessment attempt."

            )

        if candidate.status != "ACTIVE":

            raise AssessmentAttemptAccessDeniedError(

                "Candidate profile is not active."

            )

        return candidate

    # ------------------------------------------------------------------

    # TIME

    # ------------------------------------------------------------------

    @staticmethod

    def _utc_now() -> datetime:

        return datetime.now(timezone.utc)

    @classmethod

    def _normalise_datetime(

        cls,

        value: datetime,

    ) -> datetime:

        if value.tzinfo is None:

            return value.replace(tzinfo=timezone.utc)

        return value

    @classmethod

    def _is_expired(

        cls,

        expires_at: datetime | None,

    ) -> bool:

        if expires_at is None:

            return False

        return cls._utc_now() >= cls._normalise_datetime(

            expires_at

        )

    # ------------------------------------------------------------------

    # QUESTION ORDER

    # ------------------------------------------------------------------

    @staticmethod

    def order_questions_for_attempt(

        attempt: AssessmentAttempt,

        questions: list[AssessmentQuestion],

        randomize: bool,

    ) -> list[AssessmentQuestion]:

        ordered = list(questions)

        if not randomize:

            ordered.sort(

                key=lambda question: question.sequence_number

            )

            return ordered

        # Stable randomization.

        # The same attempt UUID always produces the same order.

        seed = attempt.id.int & ((1 << 64) - 1)

        rng = random.Random(seed)

        rng.shuffle(ordered)

        return ordered

    # ------------------------------------------------------------------

    # ANSWER VALIDATION

    # ------------------------------------------------------------------

    @staticmethod

    def _clean_answer(

        answer_text: str | None,

    ) -> str | None:

        if answer_text is None:

            return None

        cleaned = answer_text.strip()

        return cleaned if cleaned else None

    @classmethod

    def _validate_answer_for_question(

        cls,

        question: AssessmentQuestion,

        answer_text: str | None,

    ) -> str | None:

        answer = cls._clean_answer(answer_text)

        if answer is None:

            return None

        question_type = question.question_type

        if question_type in {

            AssessmentQuestionType.MCQ.value,

            AssessmentQuestionType.TRUE_FALSE.value,

        }:

            options = question.options or []

            if not options:

                raise AssessmentAttemptValidationError(

                    "This question has no valid answer options."

                )

            normalized_options = {

                str(option).strip().casefold()

                for option in options

            }

            if answer.casefold() not in normalized_options:

                raise AssessmentAttemptValidationError(

                    "Selected answer is not one of the available options."

                )

        elif question_type == AssessmentQuestionType.MULTIPLE_SELECT.value:

            options = question.options or []

            if not options:

                raise AssessmentAttemptValidationError(

                    "This question has no valid answer options."

                )

            normalized_options = {

                str(option).strip().casefold()

                for option in options

            }

            selected = {

                value.strip().casefold()

                for value in answer.split(",")

                if value.strip()

            }

            if not selected:

                return None

            if not selected.issubset(normalized_options):

                raise AssessmentAttemptValidationError(

                    "One or more selected answers are invalid."

                )

            # Store in canonical deterministic order.

            canonical = [

                str(option).strip()

                for option in options

                if str(option).strip().casefold() in selected

            ]

            return ",".join(canonical)

        elif question_type == AssessmentQuestionType.SHORT_ANSWER.value:

            if len(answer) > 10000:

                raise AssessmentAttemptValidationError(

                    "Answer is too long."

                )

        return answer

    # ------------------------------------------------------------------

    # EXPIRY / AUTO SUBMIT

    # ------------------------------------------------------------------

    async def expire_attempt_if_needed(

        self,

        attempt: AssessmentAttempt,

    ) -> AssessmentAttempt:

        if attempt.status != AssessmentAttemptStatus.IN_PROGRESS.value:

            return attempt

        if not self._is_expired(attempt.expires_at):

            return attempt

        await self._auto_submit_attempt(attempt)

        return attempt

    # ------------------------------------------------------------------

    # START ATTEMPT

    # ------------------------------------------------------------------

    async def start_attempt(

        self,

        user: User,

        data: AssessmentAttemptCreate,

    ) -> AssessmentAttempt:

        invitation = await self.get_invitation(

            data.invitation_id

        )

        candidate = await self.ensure_candidate_access(

            user=user,

            invitation=invitation,

        )

        if invitation.status not in {

            AssessmentInvitationStatus.INVITED.value,

            AssessmentInvitationStatus.STARTED.value,

        }:

            raise AssessmentAttemptValidationError(

                "This assessment invitation is no longer available."

            )

        if not invitation.is_active:

            raise AssessmentAttemptValidationError(

                "This assessment invitation is inactive."

            )

        if self._is_expired(invitation.expires_at):

            invitation.status = (

                AssessmentInvitationStatus.EXPIRED.value

            )

            invitation.is_active = False

            await self.db.commit()

            raise AssessmentAttemptValidationError(

                "This assessment invitation has expired."

            )

        assessment = await self.get_assessment(

            invitation.assessment_id

        )

        if assessment.status != "PUBLISHED":

            raise AssessmentAttemptValidationError(

                "Only published assessments can be attempted."

            )

        # Candidate/profile consistency.

        if candidate.id != invitation.candidate_profile_id:

            raise AssessmentAttemptValidationError(

                "Candidate profile does not match the invitation."

            )

        # --------------------------------------------------------------

        # EXISTING ACTIVE ATTEMPT

        # --------------------------------------------------------------

        active_result = await self.db.execute(

            select(AssessmentAttempt)

            .where(

                AssessmentAttempt.invitation_id

                == invitation.id,

                AssessmentAttempt.status

                == AssessmentAttemptStatus.IN_PROGRESS.value,

            )

            .order_by(

                AssessmentAttempt.attempt_number.desc()

            )

        )

        active_attempt = active_result.scalars().first()

        if active_attempt is not None:

            await self._validate_attempt_integrity(

                active_attempt

            )

            if self._is_expired(active_attempt.expires_at):

                await self._auto_submit_attempt(

                    active_attempt

                )

            else:

                return active_attempt

        # --------------------------------------------------------------

        # PREVIOUS ATTEMPTS

        # --------------------------------------------------------------

        count_result = await self.db.execute(

            select(

                func.count(AssessmentAttempt.id)

            )

            .where(

                AssessmentAttempt.invitation_id

                == invitation.id

            )

        )

        attempt_count = count_result.scalar_one()

        if attempt_count >= assessment.max_attempts:

            raise AssessmentAttemptValidationError(

                "Maximum assessment attempts have been reached."

            )

        attempt_number = attempt_count + 1

        # --------------------------------------------------------------

        # QUESTIONS

        # --------------------------------------------------------------

        question_result = await self.db.execute(

            select(AssessmentQuestion.id)

            .where(

                AssessmentQuestion.assessment_id

                == assessment.id,

                AssessmentQuestion.is_active.is_(True),

            )

        )

        question_ids = question_result.scalars().all()

        if not question_ids:

            raise AssessmentAttemptValidationError(

                "This assessment does not contain any active questions."

            )

        # --------------------------------------------------------------

        # SERVER-SIDE TIMER

        # --------------------------------------------------------------

        now = self._utc_now()

        expires_at = now + timedelta(

            minutes=assessment.duration_minutes

        )

        if invitation.expires_at is not None:

            invitation_expires_at = (

                self._normalise_datetime(

                    invitation.expires_at

                )

            )

            if invitation_expires_at < expires_at:

                expires_at = invitation_expires_at

        attempt = AssessmentAttempt(

            invitation_id=invitation.id,

            assessment_id=assessment.id,

            candidate_profile_id=invitation.candidate_profile_id,

            attempt_number=attempt_number,

            status=AssessmentAttemptStatus.IN_PROGRESS.value,

            started_at=now,

            expires_at=expires_at,

            total_questions=len(question_ids),

        )

        self.db.add(attempt)

        invitation.status = (

            AssessmentInvitationStatus.STARTED.value

        )

        invitation.started_at = (

            invitation.started_at or now

        )

        await self.db.commit()

        await self.db.refresh(attempt)

        return attempt

    # ------------------------------------------------------------------

    # SAVE ANSWER

    # ------------------------------------------------------------------

    async def save_answer(

        self,

        user: User,

        attempt_id: UUID,

        question_id: UUID,

        answer_text: str | None,

    ) -> AssessmentAnswer:

        attempt = await self.get_attempt(

            attempt_id

        )

        await self.ensure_attempt_candidate_access(

            user=user,

            attempt=attempt,

        )

        await self._validate_attempt_integrity(

            attempt

        )

        attempt = await self.expire_attempt_if_needed(

            attempt

        )

        if attempt.status != AssessmentAttemptStatus.IN_PROGRESS.value:

            raise AssessmentAttemptValidationError(

                "This assessment attempt is no longer accepting answers."

            )

        question = await self.get_question(

            question_id

        )

        if question.assessment_id != attempt.assessment_id:

            raise AssessmentAttemptValidationError(

                "The question does not belong to this assessment."

            )

        # Confirm the question is currently part of the

        # assessment's active question set.

        question_ids_result = await self.db.execute(

            select(AssessmentQuestion.id)

            .where(

                AssessmentQuestion.assessment_id

                == attempt.assessment_id,

                AssessmentQuestion.is_active.is_(True),

            )

        )

        question_ids = set(

            question_ids_result.scalars().all()

        )

        if question.id not in question_ids:

            raise AssessmentAttemptValidationError(

                "This question is not part of the active assessment."

            )

        answer_text = self._validate_answer_for_question(

            question,

            answer_text,

        )

        is_answered = answer_text is not None

        result = await self.db.execute(

            select(AssessmentAnswer)

            .where(

                AssessmentAnswer.attempt_id

                == attempt.id,

                AssessmentAnswer.question_id

                == question.id,

            )

        )

        answer = result.scalar_one_or_none()

        now = self._utc_now()

        if answer is None:

            answer = AssessmentAnswer(

                attempt_id=attempt.id,

                question_id=question.id,

                answer_text=answer_text,

                is_answered=is_answered,

                answered_at=now if is_answered else None,

            )

            self.db.add(answer)

        else:

            answer.answer_text = answer_text

            answer.is_answered = is_answered

            answer.answered_at = (

                now if is_answered else None

            )

            # A changed answer must be rescored.

            answer.is_correct = None

            answer.marks_awarded = 0.0

            answer.evaluated_at = None

        await self.db.commit()

        await self.db.refresh(answer)

        return answer

    # ------------------------------------------------------------------

    # SCORING

    # ------------------------------------------------------------------

    @staticmethod

    def _normalize_answer(

        answer: str | None,

    ) -> str:

        if answer is None:

            return ""

        return answer.strip().casefold()

    @classmethod

    def _is_correct_answer(

        cls,

        question: AssessmentQuestion,

        candidate_answer: str | None,

    ) -> bool:

        candidate = cls._normalize_answer(

            candidate_answer

        )

        correct = cls._normalize_answer(

            question.correct_answer

        )

        if not candidate or not correct:

            return False

        if (

            question.question_type

            == AssessmentQuestionType.MULTIPLE_SELECT.value

        ):

            candidate_values = {

                value.strip().casefold()

                for value in candidate.split(",")

                if value.strip()

            }

            correct_values = {

                value.strip().casefold()

                for value in correct.split(",")

                if value.strip()

            }

            return candidate_values == correct_values

        if (

            question.question_type

            == AssessmentQuestionType.SHORT_ANSWER.value

        ):

            # Current MVP behavior:

            # exact normalized answer.

            # A future evaluator can support semantic/manual grading.

            return candidate == correct

        return candidate == correct

    async def score_attempt(

        self,

        attempt: AssessmentAttempt,

    ) -> AssessmentAttempt:

        questions = await self._get_attempt_questions(

            attempt

        )

        answer_result = await self.db.execute(

            select(AssessmentAnswer)

            .where(

                AssessmentAnswer.attempt_id

                == attempt.id

            )

        )

        answers = {

            answer.question_id: answer

            for answer in answer_result.scalars().all()

        }

        total_marks = 0.0

        obtained_marks = 0.0

        correct_count = 0

        wrong_count = 0

        unanswered_count = 0

        answered_count = 0

        now = self._utc_now()

        for question in questions:

            marks = max(

                0.0,

                float(question.marks),

            )

            negative_marks = max(

                0.0,

                float(question.negative_marks),

            )

            total_marks += marks

            answer = answers.get(question.id)

            if answer is None or not answer.is_answered:

                unanswered_count += 1

                continue

            answered_count += 1

            if self._is_correct_answer(

                question,

                answer.answer_text,

            ):

                answer.is_correct = True

                answer.marks_awarded = marks

                correct_count += 1

                obtained_marks += marks

            else:

                answer.is_correct = False

                answer.marks_awarded = -negative_marks

                wrong_count += 1

                obtained_marks -= negative_marks

            answer.evaluated_at = now

        # Do not allow a negative final score.

        obtained_marks = max(

            0.0,

            obtained_marks,

        )

        percentage = (

            (obtained_marks / total_marks) * 100

            if total_marks > 0

            else 0.0

        )

        assessment = await self.get_assessment(

            attempt.assessment_id

        )

        attempt.total_questions = len(

            questions

        )

        attempt.answered_questions = answered_count

        attempt.correct_answers = correct_count

        attempt.wrong_answers = wrong_count

        attempt.unanswered_questions = unanswered_count

        attempt.total_marks = total_marks

        attempt.obtained_marks = obtained_marks

        attempt.percentage = max(

            0.0,

            min(100.0, percentage),

        )

        attempt.passed = (

            attempt.percentage

            >= assessment.passing_percentage

        )

        return attempt

    # ------------------------------------------------------------------

    # SUBMIT

    # ------------------------------------------------------------------

    async def submit_attempt(

        self,

        user: User,

        attempt_id: UUID,

    ) -> AssessmentAttempt:

        attempt = await self.get_attempt(

            attempt_id

        )

        await self.ensure_attempt_candidate_access(

            user=user,

            attempt=attempt,

        )

        await self._validate_attempt_integrity(

            attempt

        )

        if attempt.status != AssessmentAttemptStatus.IN_PROGRESS.value:

            # Idempotent behavior for already submitted attempts.

            if attempt.status in {

                AssessmentAttemptStatus.SUBMITTED.value,

                AssessmentAttemptStatus.AUTO_SUBMITTED.value,

            }:

                return attempt

            raise AssessmentAttemptValidationError(

                "This assessment attempt cannot be submitted."

            )

        expired = self._is_expired(

            attempt.expires_at

        )

        await self.score_attempt(attempt)

        attempt.submitted_at = self._utc_now()

        if expired:

            attempt.status = (

                AssessmentAttemptStatus.AUTO_SUBMITTED.value

            )

        else:

            attempt.status = (

                AssessmentAttemptStatus.SUBMITTED.value

            )

        await self._complete_invitation_if_needed(

            attempt

        )

        await self.db.commit()

        await self.db.refresh(attempt)

        return attempt

    # ------------------------------------------------------------------

    # AUTO SUBMIT

    # ------------------------------------------------------------------

    async def _auto_submit_attempt(

        self,

        attempt: AssessmentAttempt,

    ) -> None:

        if attempt.status != AssessmentAttemptStatus.IN_PROGRESS.value:

            return

        await self._validate_attempt_integrity(

            attempt

        )

        await self.score_attempt(attempt)

        attempt.status = (

            AssessmentAttemptStatus.AUTO_SUBMITTED.value

        )

        attempt.submitted_at = self._utc_now()

        await self._complete_invitation_if_needed(

            attempt

        )

        await self.db.commit()

    # ------------------------------------------------------------------

    # INVITATION LIFECYCLE

    # ------------------------------------------------------------------

    async def _complete_invitation_if_needed(

        self,

        attempt: AssessmentAttempt,

    ) -> None:

        invitation = await self.get_invitation(

            attempt.invitation_id

        )

        # Do not complete an unrelated invitation.

        if invitation.assessment_id != attempt.assessment_id:

            raise AssessmentAttemptValidationError(

                "Invitation assessment does not match attempt."

            )

        if (

            invitation.candidate_profile_id

            != attempt.candidate_profile_id

        ):

            raise AssessmentAttemptValidationError(

                "Invitation candidate does not match attempt."

            )

        # If max_attempts > 1, the invitation can remain active

        # while another attempt is still allowed.

        result = await self.db.execute(

            select(func.count(AssessmentAttempt.id))

            .where(

                AssessmentAttempt.invitation_id

                == invitation.id

            )

        )

        completed_attempt_count = result.scalar_one()

        assessment = await self.get_assessment(

            attempt.assessment_id

        )

        if completed_attempt_count >= assessment.max_attempts:

            invitation.status = (

                AssessmentInvitationStatus.COMPLETED.value

            )

            invitation.completed_at = (

                attempt.submitted_at

            )

            invitation.is_active = False

        else:

            # Keep invitation available for another allowed attempt.

            invitation.status = (

                AssessmentInvitationStatus.INVITED.value

            )

            invitation.is_active = True

    # ------------------------------------------------------------------

    # CANDIDATE ATTEMPT

    # ------------------------------------------------------------------

    async def get_candidate_attempt(

        self,

        user: User,

        attempt_id: UUID,

    ) -> AssessmentAttempt:

        attempt = await self.get_attempt(

            attempt_id

        )

        await self.ensure_attempt_candidate_access(

            user=user,

            attempt=attempt,

        )

        await self._validate_attempt_integrity(

            attempt

        )

        await self.expire_attempt_if_needed(

            attempt

        )

        return attempt

    async def list_candidate_attempts(

        self,

        user: User,

    ) -> list[AssessmentAttempt]:

        result = await self.db.execute(

            select(AssessmentAttempt)

            .join(

                CandidateProfile,

                CandidateProfile.id

                == AssessmentAttempt.candidate_profile_id,

            )

            .where(

                CandidateProfile.user_id == user.id

            )

            .order_by(

                AssessmentAttempt.created_at.desc()

            )

        )

        attempts = list(

            result.scalars().all()

        )

        for attempt in attempts:

            await self.expire_attempt_if_needed(

                attempt

            )

        return attempts

