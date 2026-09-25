from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.candidate_skill import (
    CandidateSkillCreate,
    CandidateSkillListResponse,
    CandidateSkillResponse,
    CandidateSkillUpdate,
)
from app.services.candidate_skill_service import (
    CandidateSkillServiceError,
    add_candidate_skill,
    delete_candidate_skill,
    list_candidate_skills,
    request_skill_verification,
    update_candidate_skill,
)

router = APIRouter(
    prefix="/candidate/skills",
    tags=["Candidate Skills"],
)


def handle_error(exc: CandidateSkillServiceError) -> HTTPException:
    message = str(exc)

    if (
        "not found" in message.lower()
        or "inactive" in message.lower()
    ):
        code = status.HTTP_404_NOT_FOUND
    elif (
        "already" in message.lower()
        or "cannot" in message.lower()
    ):
        code = status.HTTP_400_BAD_REQUEST
    else:
        code = status.HTTP_400_BAD_REQUEST

    return HTTPException(
        status_code=code,
        detail=message,
    )


@router.post(
    "",
    response_model=CandidateSkillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_skill(
    payload: CandidateSkillCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateSkillResponse:
    try:
        candidate_skill = await add_candidate_skill(
            db=db,
            user_id=current_user.id,
            skill_id=payload.skill_id,
            proficiency_level=payload.proficiency_level.value,
            years_of_experience=payload.years_of_experience,
            is_primary=payload.is_primary,
        )

        await db.commit()

        return CandidateSkillResponse.model_validate(
            candidate_skill
        )

    except CandidateSkillServiceError as exc:
        await db.rollback()
        raise handle_error(exc) from exc


@router.get(
    "",
    response_model=CandidateSkillListResponse,
)
async def get_candidate_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateSkillListResponse:
    try:
        skills, total = await list_candidate_skills(
            db=db,
            user_id=current_user.id,
        )

        return CandidateSkillListResponse(
            items=[
                CandidateSkillResponse.model_validate(skill)
                for skill in skills
            ],
            total=total,
        )

    except CandidateSkillServiceError as exc:
        raise handle_error(exc) from exc


@router.patch(
    "/{candidate_skill_id}",
    response_model=CandidateSkillResponse,
)
async def update_skill(
    candidate_skill_id: uuid.UUID,
    payload: CandidateSkillUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateSkillResponse:
    try:
        candidate_skill = await update_candidate_skill(
            db=db,
            user_id=current_user.id,
            candidate_skill_id=candidate_skill_id,
            proficiency_level=(
                payload.proficiency_level.value
                if payload.proficiency_level is not None
                else None
            ),
            years_of_experience=payload.years_of_experience,
            is_primary=payload.is_primary,
        )

        await db.commit()

        return CandidateSkillResponse.model_validate(
            candidate_skill
        )

    except CandidateSkillServiceError as exc:
        await db.rollback()
        raise handle_error(exc) from exc


@router.delete(
    "/{candidate_skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_skill(
    candidate_skill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await delete_candidate_skill(
            db=db,
            user_id=current_user.id,
            candidate_skill_id=candidate_skill_id,
        )

        await db.commit()

    except CandidateSkillServiceError as exc:
        await db.rollback()
        raise handle_error(exc) from exc


@router.post(
    "/{candidate_skill_id}/request-verification",
    response_model=CandidateSkillResponse,
)
async def submit_skill_for_verification(
    candidate_skill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateSkillResponse:
    try:
        candidate_skill = await request_skill_verification(
            db=db,
            user_id=current_user.id,
            candidate_skill_id=candidate_skill_id,
        )

        await db.commit()

        return CandidateSkillResponse.model_validate(
            candidate_skill
        )

    except CandidateSkillServiceError as exc:
        await db.rollback()
        raise handle_error(exc) from exc