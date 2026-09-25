from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profile import CandidateProfile
from app.models.candidate_skill import (
    CandidateSkill,
    CandidateSkillStatus,
)
from app.models.skill import Skill


class CandidateSkillServiceError(Exception):
    """Raised when a candidate skill operation is invalid."""


async def get_candidate_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> CandidateProfile:
    result = await db.execute(
        select(CandidateProfile).where(
            CandidateProfile.user_id == user_id
        )
    )

    profile = result.scalar_one_or_none()

    if profile is None:
        raise CandidateSkillServiceError(
            "Candidate profile not found."
        )

    return profile


async def get_skill(
    db: AsyncSession,
    skill_id: uuid.UUID,
) -> Skill:
    result = await db.execute(
        select(Skill).where(
            Skill.id == skill_id,
            Skill.is_active.is_(True),
        )
    )

    skill = result.scalar_one_or_none()

    if skill is None:
        raise CandidateSkillServiceError(
            "Skill not found or inactive."
        )

    return skill


async def get_candidate_skill(
    db: AsyncSession,
    candidate_skill_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CandidateSkill:
    profile = await get_candidate_profile(db, user_id)

    result = await db.execute(
        select(CandidateSkill).where(
            CandidateSkill.id == candidate_skill_id,
            CandidateSkill.candidate_profile_id == profile.id,
        )
    )

    candidate_skill = result.scalar_one_or_none()

    if candidate_skill is None:
        raise CandidateSkillServiceError(
            "Candidate skill not found."
        )

    return candidate_skill


async def list_candidate_skills(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> tuple[list[CandidateSkill], int]:
    profile = await get_candidate_profile(db, user_id)

    count_result = await db.execute(
        select(func.count(CandidateSkill.id)).where(
            CandidateSkill.candidate_profile_id == profile.id
        )
    )

    total = count_result.scalar_one()

    result = await db.execute(
        select(CandidateSkill)
        .where(
            CandidateSkill.candidate_profile_id == profile.id
        )
        .order_by(
            CandidateSkill.is_primary.desc(),
            CandidateSkill.created_at.desc(),
        )
    )

    skills = result.scalars().all()

    return list(skills), total


async def add_candidate_skill(
    db: AsyncSession,
    user_id: uuid.UUID,
    skill_id: uuid.UUID,
    proficiency_level: str,
    years_of_experience: float,
    is_primary: bool,
) -> CandidateSkill:
    profile = await get_candidate_profile(db, user_id)

    await get_skill(db, skill_id)

    existing_result = await db.execute(
        select(CandidateSkill).where(
            CandidateSkill.candidate_profile_id == profile.id,
            CandidateSkill.skill_id == skill_id,
        )
    )

    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        raise CandidateSkillServiceError(
            "This skill is already added to the candidate profile."
        )

    if is_primary:
        await clear_primary_skill(
            db,
            profile.id,
        )

    candidate_skill = CandidateSkill(
        candidate_profile_id=profile.id,
        skill_id=skill_id,
        proficiency_level=proficiency_level,
        years_of_experience=years_of_experience,
        status=CandidateSkillStatus.SELF_DECLARED.value,
        is_primary=is_primary,
    )

    db.add(candidate_skill)

    await db.flush()
    await db.refresh(candidate_skill)

    return candidate_skill


async def update_candidate_skill(
    db: AsyncSession,
    user_id: uuid.UUID,
    candidate_skill_id: uuid.UUID,
    proficiency_level: str | None = None,
    years_of_experience: float | None = None,
    is_primary: bool | None = None,
) -> CandidateSkill:
    candidate_skill = await get_candidate_skill(
        db,
        candidate_skill_id,
        user_id,
    )

    if candidate_skill.status in {
        CandidateSkillStatus.REVOKED.value,
    }:
        raise CandidateSkillServiceError(
            "Revoked skills cannot be modified."
        )

    if proficiency_level is not None:
        candidate_skill.proficiency_level = proficiency_level

    if years_of_experience is not None:
        candidate_skill.years_of_experience = years_of_experience

    if is_primary is not None:
        if is_primary:
            await clear_primary_skill(
                db,
                candidate_skill.candidate_profile_id,
                exclude_id=candidate_skill.id,
            )

        candidate_skill.is_primary = is_primary

    # A change to a verified skill requires re-verification.
    if candidate_skill.status == CandidateSkillStatus.VERIFIED.value:
        candidate_skill.status = CandidateSkillStatus.PENDING.value
        candidate_skill.verified_by_user_id = None
        candidate_skill.verified_at = None
        candidate_skill.verification_notes = (
            "Skill details changed and require re-verification."
        )

    await db.flush()
    await db.refresh(candidate_skill)

    return candidate_skill


async def delete_candidate_skill(
    db: AsyncSession,
    user_id: uuid.UUID,
    candidate_skill_id: uuid.UUID,
) -> None:
    candidate_skill = await get_candidate_skill(
        db,
        candidate_skill_id,
        user_id,
    )

    if candidate_skill.status == CandidateSkillStatus.VERIFIED.value:
        raise CandidateSkillServiceError(
            "Verified skills cannot be deleted. "
            "Request revocation instead."
        )

    if candidate_skill.status == CandidateSkillStatus.REVOKED.value:
        raise CandidateSkillServiceError(
            "Revoked skills cannot be deleted."
        )

    await db.delete(candidate_skill)
    await db.flush()


async def request_skill_verification(
    db: AsyncSession,
    user_id: uuid.UUID,
    candidate_skill_id: uuid.UUID,
) -> CandidateSkill:
    candidate_skill = await get_candidate_skill(
        db,
        candidate_skill_id,
        user_id,
    )

    if candidate_skill.status == CandidateSkillStatus.VERIFIED.value:
        raise CandidateSkillServiceError(
            "This skill is already verified."
        )

    if candidate_skill.status == CandidateSkillStatus.REVOKED.value:
        raise CandidateSkillServiceError(
            "A revoked skill cannot be submitted for verification."
        )

    candidate_skill.status = CandidateSkillStatus.PENDING.value
    candidate_skill.verification_notes = None

    await db.flush()
    await db.refresh(candidate_skill)

    return candidate_skill


async def clear_primary_skill(
    db: AsyncSession,
    candidate_profile_id: uuid.UUID,
    exclude_id: uuid.UUID | None = None,
) -> None:
    query = select(CandidateSkill).where(
        CandidateSkill.candidate_profile_id == candidate_profile_id,
        CandidateSkill.is_primary.is_(True),
    )

    if exclude_id is not None:
        query = query.where(
            CandidateSkill.id != exclude_id
        )

    result = await db.execute(query)

    existing_primary_skills = result.scalars().all()

    for skill in existing_primary_skills:
        skill.is_primary = False