from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate_skill import (
    CandidateSkill,
    CandidateSkillStatus,
)
from app.models.user import User


class CandidateSkillVerificationServiceError(Exception):
    """Base error for candidate skill verification."""


class CandidateSkillVerificationNotFoundError(
    CandidateSkillVerificationServiceError
):
    """Candidate skill was not found."""


class CandidateSkillVerificationAccessDeniedError(
    CandidateSkillVerificationServiceError
):
    """User is not authorized to verify the skill."""


class CandidateSkillVerificationValidationError(
    CandidateSkillVerificationServiceError
):
    """Verification request is invalid."""


class CandidateSkillVerificationService:

    @staticmethod
    async def get_skill_for_verification(
        db: AsyncSession,
        candidate_skill_id: uuid.UUID,
    ) -> CandidateSkill:
        result = await db.execute(
            select(CandidateSkill)
            .options(
                selectinload(CandidateSkill.candidate_profile),
                selectinload(CandidateSkill.skill),
            )
            .where(
                CandidateSkill.id == candidate_skill_id
            )
        )

        candidate_skill = result.scalar_one_or_none()

        if candidate_skill is None:
            raise CandidateSkillVerificationNotFoundError(
                "Candidate skill not found."
            )

        return candidate_skill

    @staticmethod
    def ensure_verifier_is_not_candidate(
        current_user: User,
        candidate_skill: CandidateSkill,
    ) -> None:
        candidate_profile = candidate_skill.candidate_profile

        if candidate_profile is None:
            raise CandidateSkillVerificationValidationError(
                "Candidate profile not found."
            )

        if candidate_profile.user_id == current_user.id:
            raise CandidateSkillVerificationAccessDeniedError(
                "A candidate cannot verify their own skill."
            )

    @staticmethod
    def ensure_verification_status(
        candidate_skill: CandidateSkill,
    ) -> None:
        allowed_statuses = {
            CandidateSkillStatus.SELF_DECLARED.value,
            CandidateSkillStatus.PENDING.value,
        }

        if candidate_skill.status not in allowed_statuses:
            raise CandidateSkillVerificationValidationError(
                "Only self-declared or pending skills can be verified."
            )

    @classmethod
    async def verify_candidate_skill(
        cls,
        db: AsyncSession,
        current_user: User,
        candidate_skill_id: uuid.UUID,
        *,
        notes: str | None = None,
        expires_at: datetime | None = None,
    ) -> CandidateSkill:
        candidate_skill = await cls.get_skill_for_verification(
            db=db,
            candidate_skill_id=candidate_skill_id,
        )

        cls.ensure_verifier_is_not_candidate(
            current_user=current_user,
            candidate_skill=candidate_skill,
        )

        cls.ensure_verification_status(candidate_skill)

        if expires_at is not None:
            now = datetime.now(timezone.utc)

            if expires_at <= now:
                raise CandidateSkillVerificationValidationError(
                    "Expiry date must be in the future."
                )

        candidate_skill.status = (
            CandidateSkillStatus.VERIFIED.value
        )
        candidate_skill.verified_by_user_id = current_user.id
        candidate_skill.verified_at = datetime.now(timezone.utc)
        candidate_skill.expires_at = expires_at
        candidate_skill.verification_notes = (
            notes.strip() if notes else None
        )

        await db.commit()
        await db.refresh(candidate_skill)

        return candidate_skill

    @classmethod
    async def reject_candidate_skill(
        cls,
        db: AsyncSession,
        current_user: User,
        candidate_skill_id: uuid.UUID,
        *,
        notes: str,
    ) -> CandidateSkill:
        candidate_skill = await cls.get_skill_for_verification(
            db=db,
            candidate_skill_id=candidate_skill_id,
        )

        cls.ensure_verifier_is_not_candidate(
            current_user=current_user,
            candidate_skill=candidate_skill,
        )

        cls.ensure_verification_status(candidate_skill)

        if not notes.strip():
            raise CandidateSkillVerificationValidationError(
                "Rejection reason is required."
            )

        candidate_skill.status = (
            CandidateSkillStatus.REJECTED.value
        )
        candidate_skill.verified_by_user_id = current_user.id
        candidate_skill.verified_at = datetime.now(timezone.utc)
        candidate_skill.verification_notes = notes.strip()

        await db.commit()
        await db.refresh(candidate_skill)

        return candidate_skill

    @classmethod
    async def revoke_candidate_skill(
        cls,
        db: AsyncSession,
        current_user: User,
        candidate_skill_id: uuid.UUID,
        *,
        notes: str,
    ) -> CandidateSkill:
        candidate_skill = await cls.get_skill_for_verification(
            db=db,
            candidate_skill_id=candidate_skill_id,
        )

        cls.ensure_verifier_is_not_candidate(
            current_user=current_user,
            candidate_skill=candidate_skill,
        )

        if candidate_skill.status != CandidateSkillStatus.VERIFIED.value:
            raise CandidateSkillVerificationValidationError(
                "Only verified skills can be revoked."
            )

        if not notes.strip():
            raise CandidateSkillVerificationValidationError(
                "Revocation reason is required."
            )

        candidate_skill.status = (
            CandidateSkillStatus.REVOKED.value
        )
        candidate_skill.verification_notes = notes.strip()

        await db.commit()
        await db.refresh(candidate_skill)

        return candidate_skill