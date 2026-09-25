from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    VIEW_ASSESSMENT_RESULTS,
    VIEW_OWN_ASSESSMENT_RESULTS,
    require_permissions,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_result import (
    AssessmentDetailedResult,
    AssessmentEmployerResult,
    AssessmentResultAnswer,
    AssessmentResultAnswerListResponse,
    AssessmentResultSummary,
)
from app.services.assessment_result_service import (
    AssessmentResultAccessDeniedError,
    AssessmentResultNotFoundError,
    AssessmentResultService,
    AssessmentResultServiceError,
    AssessmentResultValidationError,
)


router = APIRouter(
    prefix="/assessment-results",
    tags=["Assessment Results"],
)


def handle_service_error(
    exc: AssessmentResultServiceError,
) -> HTTPException:
    if isinstance(
        exc,
        AssessmentResultNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(
        exc,
        AssessmentResultAccessDeniedError,
    ):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(
        exc,
        AssessmentResultValidationError,
    ):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


# ----------------------------------------------------------------------
# CANDIDATE RESULT SUMMARY
# ----------------------------------------------------------------------


@router.get(
    "/candidate/{attempt_id}",
    response_model=AssessmentResultSummary,
    dependencies=[
        Depends(
            require_permissions(
                VIEW_OWN_ASSESSMENT_RESULTS,
            )
        )
    ],
)
async def get_candidate_result(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AssessmentResultService(db)

    try:
        attempt = await service.get_candidate_result(
            user=current_user,
            attempt_id=attempt_id,
        )

        return AssessmentResultSummary(
            attempt_id=attempt.attempt_id,
            assessment_id=attempt.assessment_id,
            attempt_number=attempt.attempt_number,
            status=attempt.status,
            submitted_at=attempt.submitted_at,
            total_questions=attempt.total_questions,
            answered_questions=attempt.answered_questions,
            correct_answers=attempt.correct_answers,
            wrong_answers=attempt.wrong_answers,
            unanswered_questions=attempt.unanswered_questions,
            total_marks=attempt.total_marks,
            obtained_marks=attempt.obtained_marks,
            percentage=attempt.percentage,
            passed=attempt.passed,
        )

    except AssessmentResultServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# CANDIDATE DETAILED RESULT
# ----------------------------------------------------------------------


@router.get(
    "/candidate/{attempt_id}/details",
    response_model=AssessmentDetailedResult,
    dependencies=[
        Depends(
            require_permissions(
                VIEW_OWN_ASSESSMENT_RESULTS,
            )
        )
    ],
)
async def get_candidate_detailed_result(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AssessmentResultService(db)

    try:
        result = await service.get_candidate_result(
            user=current_user,
            attempt_id=attempt_id,
        )

        questions = await service.get_result_questions(
            user=current_user,
            attempt_id=attempt_id,
        )

        answers = await service.get_candidate_result_answers(
            user=current_user,
            attempt_id=attempt_id,
        )

        summary = AssessmentResultSummary(
            attempt_id=result.attempt_id,
            assessment_id=result.assessment_id,
            attempt_number=result.attempt_number,
            status=result.status,
            submitted_at=result.submitted_at,
            total_questions=result.total_questions,
            answered_questions=result.answered_questions,
            correct_answers=result.correct_answers,
            wrong_answers=result.wrong_answers,
            unanswered_questions=result.unanswered_questions,
            total_marks=result.total_marks,
            obtained_marks=result.obtained_marks,
            percentage=result.percentage,
            passed=result.passed,
        )

        return AssessmentDetailedResult(
            summary=summary,
            questions=questions,
            answers=answers,
        )

    except AssessmentResultServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# EMPLOYER RESULT
# ----------------------------------------------------------------------


@router.get(
    "/employer/{attempt_id}",
    response_model=AssessmentEmployerResult,
    dependencies=[
        Depends(
            require_permissions(
                VIEW_ASSESSMENT_RESULTS,
            )
        )
    ],
)
async def get_employer_result(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AssessmentResultService(db)

    try:
        attempt = await service.get_employer_result(
            user=current_user,
            attempt_id=attempt_id,
        )

        return AssessmentEmployerResult(
            attempt_id=attempt.attempt_id,
            assessment_id=attempt.assessment_id,
            candidate_profile_id=attempt.candidate_profile_id,
            attempt_number=attempt.attempt_number,
            status=attempt.status,
            submitted_at=attempt.submitted_at,
            total_questions=attempt.total_questions,
            answered_questions=attempt.answered_questions,
            correct_answers=attempt.correct_answers,
            wrong_answers=attempt.wrong_answers,
            unanswered_questions=attempt.unanswered_questions,
            total_marks=attempt.total_marks,
            obtained_marks=attempt.obtained_marks,
            percentage=attempt.percentage,
            passed=attempt.passed,
        )

    except AssessmentResultServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# EMPLOYER ANSWERS
# ----------------------------------------------------------------------


@router.get(
    "/employer/{attempt_id}/answers",
    response_model=AssessmentResultAnswerListResponse,
    dependencies=[
        Depends(
            require_permissions(
                VIEW_ASSESSMENT_RESULTS,
            )
        )
    ],
)
async def get_employer_result_answers(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AssessmentResultService(db)

    try:
        answers = await service.get_employer_result_answers(
            user=current_user,
            attempt_id=attempt_id,
        )

        return AssessmentResultAnswerListResponse(
            items=answers,
            total=len(answers),
        )

    except AssessmentResultServiceError as exc:
        raise handle_service_error(exc) from exc
