from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.assessment_question import (
    AssessmentQuestionDifficulty,
    AssessmentQuestionType,
)
from app.models.user import User
from app.schemas.assessment_question import (
    AssessmentQuestionCandidateListResponse,
    AssessmentQuestionCandidateResponse,
    AssessmentQuestionCreate,
    AssessmentQuestionListResponse,
    AssessmentQuestionResponse,
    AssessmentQuestionUpdate,
)
from app.services.assessment_question_service import (
    AssessmentQuestionAccessDeniedError,
    AssessmentQuestionNotFoundError,
    AssessmentQuestionService,
    AssessmentQuestionServiceError,
    AssessmentQuestionValidationError,
)

router = APIRouter(
    prefix="/assessments",
    tags=["Assessment Questions"],
)


@router.post(
    "/{assessment_id}/questions",
    response_model=AssessmentQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question(
    assessment_id: uuid.UUID,
    payload: AssessmentQuestionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentQuestionResponse:
    """Create a question in an assessment."""

    service = AssessmentQuestionService(db)

    try:
        question = await service.create_question(
            user=current_user,
            assessment_id=assessment_id,
            question_text=payload.question_text,
            question_type=payload.question_type,
            difficulty=payload.difficulty.value,
            options=payload.options,
            correct_answer=payload.correct_answer,
            explanation=payload.explanation,
            marks=payload.marks,
            negative_marks=payload.negative_marks,
            skill_id=payload.skill_id,
            sequence_number=payload.sequence_number,
        )

        return AssessmentQuestionResponse.model_validate(
            question
        )

    except AssessmentQuestionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{assessment_id}/questions",
    response_model=AssessmentQuestionListResponse,
)
async def list_questions(
    assessment_id: uuid.UUID,
    include_inactive: bool = Query(
        default=False
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentQuestionListResponse:
    """
    List assessment questions for authorized users.

    correct_answer is included because this is an
    employer/admin management endpoint.
    """

    service = AssessmentQuestionService(db)

    try:
        assessment = await service.get_assessment(
            assessment_id
        )

        await service.ensure_manager_access(
            current_user,
            assessment,
        )

        questions, total = await service.list_questions(
            assessment_id=assessment_id,
            include_inactive=include_inactive,
        )

        return AssessmentQuestionListResponse(
            items=[
                AssessmentQuestionResponse.model_validate(
                    question
                )
                for question in questions
            ],
            total=total,
        )

    except AssessmentQuestionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/questions/{question_id}",
    response_model=AssessmentQuestionResponse,
)
async def update_question(
    question_id: uuid.UUID,
    payload: AssessmentQuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentQuestionResponse:
    """Update an assessment question."""

    service = AssessmentQuestionService(db)

    updates = payload.model_dump(
        exclude_unset=True
    )

    try:
        question = await service.update_question(
            user=current_user,
            question_id=question_id,
            **updates,
        )

        return AssessmentQuestionResponse.model_validate(
            question
        )

    except AssessmentQuestionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def deactivate_question(
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate an assessment question."""

    service = AssessmentQuestionService(db)

    try:
        await service.delete_question(
            user=current_user,
            question_id=question_id,
        )

    except AssessmentQuestionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{assessment_id}/candidate-questions",
    response_model=AssessmentQuestionCandidateListResponse,
)
async def list_candidate_questions(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentQuestionCandidateListResponse:
    """
    Get questions for a candidate.

    IMPORTANT:
    This endpoint deliberately strips correct_answer
    and explanation before returning data.
    """

    if current_user.account_type != "CANDIDATE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access assessment questions.",
        )

    service = AssessmentQuestionService(db)

    try:
        questions, total = (
            await service.list_candidate_questions(
                assessment_id=assessment_id,
            )
        )

        items = [
            AssessmentQuestionCandidateResponse(
                id=question.id,
                assessment_id=question.assessment_id,
                question_text=question.question_text,
                question_type=AssessmentQuestionType(
                    question.question_type
                ),
                difficulty=AssessmentQuestionDifficulty(
                    question.difficulty
                ),
                options=question.options,
                marks=question.marks,
                sequence_number=question.sequence_number,
            )
            for question in questions
        ]

        return AssessmentQuestionCandidateListResponse(
            items=items,
            total=total,
        )

    except AssessmentQuestionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except AssessmentQuestionServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc