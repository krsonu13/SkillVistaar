from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    VERIFY_SKILLS,
    VIEW_SKILLS,
    require_permissions,
)
from app.db.session import get_db
from app.models.candidate_skill import CandidateSkill
from app.models.user import User
from app.schemas.candidate_skill import CandidateSkillResponse

router = APIRouter(
    prefix="/candidate-skill-verification",
    tags=["Candidate Skill Verification"],
)


@router.get(
    "/{candidate_skill_id}",
    response_model=CandidateSkillResponse,
)
async def get_candidate_skill_for_verification(
    candidate_skill_id: UUID,
    current_user_and_roles=Depends(
        require_permissions(VIEW_SKILLS)
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CandidateSkill).where(
            CandidateSkill.id == candidate_skill_id
        )
    )

    candidate_skill = result.scalar_one_or_none()

    if candidate_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate skill not found.",
        )

    return candidate_skill


@router.post(
    "/{candidate_skill_id}/verify",
    response_model=CandidateSkillResponse,
)
async def verify_candidate_skill(
    candidate_skill_id: UUID,
    current_user_and_roles=Depends(
        require_permissions(VERIFY_SKILLS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _ = current_user_and_roles

    result = await db.execute(
        select(CandidateSkill).where(
            CandidateSkill.id == candidate_skill_id
        )
    )

    candidate_skill = result.scalar_one_or_none()

    if candidate_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate skill not found.",
        )

    candidate_skill.status = "VERIFIED"
    candidate_skill.verified_by_user_id = current_user.id

    await db.commit()
    await db.refresh(candidate_skill)

    return candidate_skill


@router.post(
    "/{candidate_skill_id}/reject",
    response_model=CandidateSkillResponse,
)
async def reject_candidate_skill(
    candidate_skill_id: UUID,
    current_user_and_roles=Depends(
        require_permissions(VERIFY_SKILLS)
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CandidateSkill).where(
            CandidateSkill.id == candidate_skill_id
        )
    )

    candidate_skill = result.scalar_one_or_none()

    if candidate_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate skill not found.",
        )

    candidate_skill.status = "REJECTED"

    await db.commit()
    await db.refresh(candidate_skill)

    return candidate_skill