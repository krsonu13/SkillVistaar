from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    CREATE_JOB,
    UPDATE_JOB,
    VIEW_JOBS,
    require_permissions,
)
from app.db.session import get_db
from app.schemas.job_screening import (
    JobScreeningQuestionCreate,
    JobScreeningQuestionListResponse,
    JobScreeningQuestionResponse,
    JobScreeningQuestionUpdate,
)
from app.services.job_screening_service import (
    JobScreeningAccessDeniedError,
    JobScreeningNotFoundError,
    JobScreeningService,
    JobScreeningServiceError,
    JobScreeningValidationError,
)

router = APIRouter(
    prefix="/jobs/{job_id}/screening",
    tags=["Job Screening"],
)


@router.get(
    "",
    response_model=JobScreeningQuestionListResponse,
)
async def list_screening_questions(
    job_id: UUID,
    current_user_data=Depends(
        require_permissions(VIEW_JOBS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    service = JobScreeningService(db)

    try:
        questions = await service.list_questions(
            job_id=job_id,
            user_id=current_user.id,
            management_access=True,
        )

        return {
            "questions": questions,
            "total": len(questions),
        }

    except JobScreeningNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except JobScreeningAccessDeniedError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=JobScreeningQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_screening_question(
    job_id: UUID,
    payload: JobScreeningQuestionCreate,
    current_user_data=Depends(
        require_permissions(CREATE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    service = JobScreeningService(db)

    try:
        return await service.create_question(
            job_id=job_id,
            user_id=current_user.id,
            question=payload.question,
            question_type=payload.question_type,
            options=payload.options,
            is_required=payload.is_required,
            display_order=payload.display_order,
        )

    except JobScreeningNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except JobScreeningAccessDeniedError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    except JobScreeningValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{question_id}",
    response_model=JobScreeningQuestionResponse,
)
async def update_screening_question(
    job_id: UUID,
    question_id: UUID,
    payload: JobScreeningQuestionUpdate,
    current_user_data=Depends(
        require_permissions(UPDATE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    service = JobScreeningService(db)

    try:
        return await service.update_question(
            job_id=job_id,
            question_id=question_id,
            user_id=current_user.id,
            question=payload.question,
            question_type=payload.question_type,
            options=payload.options,
            is_required=payload.is_required,
            display_order=payload.display_order,
        )

    except JobScreeningNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except JobScreeningAccessDeniedError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    except JobScreeningValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_screening_question(
    job_id: UUID,
    question_id: UUID,
    current_user_data=Depends(
        require_permissions(UPDATE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    service = JobScreeningService(db)

    try:
        await service.delete_question(
            job_id=job_id,
            question_id=question_id,
            user_id=current_user.id,
        )

    except JobScreeningNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except JobScreeningAccessDeniedError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    except JobScreeningValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc