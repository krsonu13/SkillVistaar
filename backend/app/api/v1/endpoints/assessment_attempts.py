from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_candidate
from app.db.session import get_db
from app.models.assessment_answer import AssessmentAnswer
from app.models.assessment_question import AssessmentQuestion
from app.models.user import User
from app.schemas.assessment_answer import (
    AssessmentAnswerCreate,
    AssessmentAnswerResponse,
)
from app.schemas.assessment_attempt import (
    AssessmentAttemptCandidateQuestion,
    AssessmentAttemptCreate,
    AssessmentAttemptListResponse,
    AssessmentAttemptResponse,
    AssessmentAttemptSessionResponse,
    AssessmentAttemptStartResponse,
    AssessmentAttemptSubmitResponse,
)
from app.services.assessment_attempt_service import (
    AssessmentAttemptAccessDeniedError,
    AssessmentAttemptNotFoundError,
    AssessmentAttemptService,
    AssessmentAttemptServiceError,
    AssessmentAttemptValidationError,
)


router = APIRouter(
    prefix="/assessment-attempts",
    tags=["Assessment Attempts"],
)


# ----------------------------------------------------------------------
# SERVICE ERROR HANDLING
# ----------------------------------------------------------------------


def handle_service_error(
    exc: AssessmentAttemptServiceError,
) -> HTTPException:
    if isinstance(exc, AssessmentAttemptNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, AssessmentAttemptAccessDeniedError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(exc, AssessmentAttemptValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


# ----------------------------------------------------------------------
# START ATTEMPT
# ----------------------------------------------------------------------


@router.post(
    "/start",
    response_model=AssessmentAttemptStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_assessment_attempt(
    data: AssessmentAttemptCreate,
    current_user: User = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
):
    """
    Start or resume the candidate's assessment attempt.

    Server-side controls:
    - candidate ownership
    - invitation validity
    - assessment publication
    - maximum attempts
    - server-side expiry
    - candidate profile status
    """

    service = AssessmentAttemptService(db)

    try:
        return await service.start_attempt(
            user=current_user,
            data=data,
        )

    except AssessmentAttemptServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# GET CURRENT ATTEMPT SESSION
# ----------------------------------------------------------------------


@router.get(
    "/{attempt_id}/session",
    response_model=AssessmentAttemptSessionResponse,
)
async def get_attempt_session(
    attempt_id: UUID,
    current_user: User = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the candidate's assessment session.

    Security guarantees:
    - candidate can access only their own attempt
    - expired attempts are automatically submitted
    - correct answers are never exposed
    - explanations are never exposed
    - question order is stable for the lifetime of the attempt
    """

    service = AssessmentAttemptService(db)

    try:
        attempt = await service.get_candidate_attempt(
            user=current_user,
            attempt_id=attempt_id,
        )

        assessment = await service.get_assessment(
            attempt.assessment_id
        )

        # --------------------------------------------------------------
        # Only an active attempt can expose the assessment session.
        # Submitted attempts are retrieved through the result/history
        # endpoints instead of being treated as an active session.
        # --------------------------------------------------------------

        if attempt.status not in {"IN_PROGRESS"}:
            raise AssessmentAttemptValidationError(
                "This assessment attempt is no longer active."
            )

        # --------------------------------------------------------------
        # Load active questions
        # --------------------------------------------------------------

        result = await db.execute(
            select(AssessmentQuestion)
            .where(
                AssessmentQuestion.assessment_id
                == attempt.assessment_id,
                AssessmentQuestion.is_active.is_(True),
            )
        )

        questions = list(result.scalars().all())

        if not questions:
            raise AssessmentAttemptValidationError(
                "This assessment does not contain any active questions."
            )

        # --------------------------------------------------------------
        # Stable ordering
        # --------------------------------------------------------------

        questions = service.order_questions_for_attempt(
            attempt=attempt,
            questions=questions,
            randomize=assessment.randomize_questions,
        )

        # --------------------------------------------------------------
        # Load candidate's saved answers
        # --------------------------------------------------------------

        answer_result = await db.execute(
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

        # --------------------------------------------------------------
        # Candidate-safe question response
        # --------------------------------------------------------------

        candidate_questions = []

        for question in questions:
            answer = answers.get(question.id)

            candidate_questions.append(
                AssessmentAttemptCandidateQuestion(
                    id=question.id,
                    question_text=question.question_text,
                    question_type=question.question_type,
                    difficulty=question.difficulty,
                    options=question.options,
                    marks=question.marks,
                    negative_marks=question.negative_marks,
                    skill_id=question.skill_id,
                    sequence_number=question.sequence_number,
                    answer_text=(
                        answer.answer_text
                        if answer is not None
                        else None
                    ),
                )
            )

        return AssessmentAttemptSessionResponse(
            attempt=attempt,
            questions=candidate_questions,
            server_time=datetime.now(timezone.utc),
            expires_at=attempt.expires_at,
        )

    except AssessmentAttemptServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# SAVE ANSWER
# ----------------------------------------------------------------------


@router.post(
    "/{attempt_id}/answers",
    response_model=AssessmentAnswerResponse,
)
async def save_assessment_answer(
    attempt_id: UUID,
    data: AssessmentAnswerCreate,
    current_user: User = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
):
    """
    Save or update one candidate answer.

    The service validates:
    - candidate ownership
    - attempt integrity
    - attempt timer
    - question ownership
    - active question membership
    - answer type/options
    """

    service = AssessmentAttemptService(db)

    try:
        return await service.save_answer(
            user=current_user,
            attempt_id=attempt_id,
            question_id=data.question_id,
            answer_text=data.answer_text,
        )

    except AssessmentAttemptServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# SUBMIT ATTEMPT
# ----------------------------------------------------------------------


@router.post(
    "/{attempt_id}/submit",
    response_model=AssessmentAttemptSubmitResponse,
)
async def submit_assessment_attempt(
    attempt_id: UUID,
    current_user: User = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit the assessment.

    The server calculates:
    - correct answers
    - wrong answers
    - unanswered questions
    - total marks
    - obtained marks
    - percentage
    - pass/fail
    - manual vs automatic submission

    Repeated submission of an already-submitted attempt is
    safely handled by the service.
    """

    service = AssessmentAttemptService(db)

    try:
        return await service.submit_attempt(
            user=current_user,
            attempt_id=attempt_id,
        )

    except AssessmentAttemptServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# GET ONE ATTEMPT
# ----------------------------------------------------------------------


@router.get(
    "/{attempt_id}",
    response_model=AssessmentAttemptResponse,
)
async def get_assessment_attempt(
    attempt_id: UUID,
    current_user: User = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current candidate's own assessment attempt.

    This endpoint does not expose individual answer evaluation
    or the correct-answer key.
    """

    service = AssessmentAttemptService(db)

    try:
        return await service.get_candidate_attempt(
            user=current_user,
            attempt_id=attempt_id,
        )

    except AssessmentAttemptServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# LIST MY ATTEMPTS
# ----------------------------------------------------------------------


@router.get(
    "/",
    response_model=AssessmentAttemptListResponse,
)
async def list_my_assessment_attempts(
    current_user: User = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the current candidate's assessment history.
    """

    service = AssessmentAttemptService(db)

    try:
        attempts = await service.list_candidate_attempts(
            user=current_user,
        )

        return AssessmentAttemptListResponse(
            items=attempts,
            total=len(attempts),
        )

    except AssessmentAttemptServiceError as exc:
        raise handle_service_error(exc) from exc