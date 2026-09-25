from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate_credential import (
    CandidateCredential,
    CredentialStatus,
)
from app.models.candidate_credential_skill import CandidateCredentialSkill
from app.models.skill import Skill
from app.models.user import User


class CandidateCredentialSkillServiceError(Exception):
    """Base error for credential-skill operations."""


class CandidateCredentialSkillNotFoundError(
    CandidateCredentialSkillServiceError
):
    """Requested credential, skill, or mapping was not found."""


class CandidateCredentialSkillAccessDeniedError(
    CandidateCredentialSkillServiceError
):
    """User is not authorized to perform the operation."""


class CandidateCredentialSkillValidationError(
    CandidateCredentialSkillServiceError
):
    """Credential-skill operation failed validation."""


class CandidateCredentialSkillService:

    @staticmethod
    async def get_credential(
        db: AsyncSession,
        credential_id: uuid.UUID,
    ) -> CandidateCredential:
        result = await db.execute(
            select(CandidateCredential)
            .options(
                selectinload(CandidateCredential.candidate_profile),
            )
            .where(CandidateCredential.id == credential_id)
        )

        credential = result.scalar_one_or_none()

        if credential is None:
            raise CandidateCredentialSkillNotFoundError(
                "Credential not found."
            )

        return credential

    @staticmethod
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
            raise CandidateCredentialSkillNotFoundError(
                "Active skill not found."
            )

        return skill

    @staticmethod
    def ensure_candidate_owns_credential(
        current_user: User,
        credential: CandidateCredential,
    ) -> None:
        candidate_profile = credential.candidate_profile

        if candidate_profile is None:
            raise CandidateCredentialSkillValidationError(
                "Credential is not associated with a candidate profile."
            )

        if candidate_profile.user_id != current_user.id:
            raise CandidateCredentialSkillAccessDeniedError(
                "You can only manage your own credentials."
            )

    @staticmethod
    def ensure_credential_can_be_mapped(
        credential: CandidateCredential,
    ) -> None:
        blocked_statuses = {
            CredentialStatus.REVOKED.value,
            CredentialStatus.REJECTED.value,
            CredentialStatus.EXPIRED.value,
        }

        if credential.status in blocked_statuses:
            raise CandidateCredentialSkillValidationError(
                "This credential cannot be mapped to a skill "
                f"because its status is {credential.status}."
            )

    @staticmethod
    async def get_mapping(
        db: AsyncSession,
        mapping_id: uuid.UUID,
    ) -> CandidateCredentialSkill:
        result = await db.execute(
            select(CandidateCredentialSkill)
            .options(
                selectinload(CandidateCredentialSkill.credential),
                selectinload(CandidateCredentialSkill.skill),
            )
            .where(CandidateCredentialSkill.id == mapping_id)
        )

        mapping = result.scalar_one_or_none()

        if mapping is None:
            raise CandidateCredentialSkillNotFoundError(
                "Credential-skill mapping not found."
            )

        return mapping

    @staticmethod
    async def ensure_unique_mapping(
        db: AsyncSession,
        credential_id: uuid.UUID,
        skill_id: uuid.UUID,
    ) -> None:
        result = await db.execute(
            select(CandidateCredentialSkill).where(
                CandidateCredentialSkill.credential_id == credential_id,
                CandidateCredentialSkill.skill_id == skill_id,
            )
        )

        if result.scalar_one_or_none() is not None:
            raise CandidateCredentialSkillValidationError(
                "This skill is already mapped to the credential."
            )

    @classmethod
    async def add_skill_to_credential(
        cls,
        db: AsyncSession,
        current_user: User,
        credential_id: uuid.UUID,
        skill_id: uuid.UUID,
        is_primary: bool = False,
    ) -> CandidateCredentialSkill:
        credential = await cls.get_credential(
            db,
            credential_id,
        )

        cls.ensure_candidate_owns_credential(
            current_user,
            credential,
        )

        cls.ensure_credential_can_be_mapped(
            credential,
        )

        skill = await cls.get_skill(
            db,
            skill_id,
        )

        await cls.ensure_unique_mapping(
            db,
            credential_id,
            skill_id,
        )

        if is_primary:
            result = await db.execute(
                select(CandidateCredentialSkill).where(
                    CandidateCredentialSkill.credential_id == credential_id,
                    CandidateCredentialSkill.is_primary.is_(True),
                )
            )

            existing_primary = result.scalars().all()

            for existing in existing_primary:
                existing.is_primary = False

        mapping = CandidateCredentialSkill(
            credential_id=credential.id,
            skill_id=skill.id,
            is_primary=is_primary,
        )

        db.add(mapping)

        await db.commit()
        await db.refresh(mapping)

        return mapping

    @classmethod
    async def remove_skill_from_credential(
        cls,
        db: AsyncSession,
        current_user: User,
        mapping_id: uuid.UUID,
    ) -> None:
        mapping = await cls.get_mapping(
            db,
            mapping_id,
        )

        credential = await cls.get_credential(
            db,
            mapping.credential_id,
        )

        cls.ensure_candidate_owns_credential(
            current_user,
            credential,
        )

        await db.delete(mapping)
        await db.commit()

    @staticmethod
    async def list_credential_skills(
        db: AsyncSession,
        credential_id: uuid.UUID,
    ) -> list[CandidateCredentialSkill]:
        result = await db.execute(
            select(CandidateCredentialSkill)
            .options(
                selectinload(CandidateCredentialSkill.skill),
            )
            .where(
                CandidateCredentialSkill.credential_id == credential_id
            )
            .order_by(
                CandidateCredentialSkill.is_primary.desc(),
                CandidateCredentialSkill.created_at.asc(),
            )
        )

        return list(result.scalars().all())

    @staticmethod
    async def get_verified_credential_skill_ids(
        db: AsyncSession,
        credential_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        credential_result = await db.execute(
            select(CandidateCredential.status).where(
                CandidateCredential.id == credential_id
            )
        )

        credential_status = credential_result.scalar_one_or_none()

        if credential_status is None:
            raise CandidateCredentialSkillNotFoundError(
                "Credential not found."
            )

        if credential_status != CredentialStatus.VERIFIED.value:
            raise CandidateCredentialSkillValidationError(
                "Only a verified credential can establish verified skills."
            )

        result = await db.execute(
            select(CandidateCredentialSkill.skill_id).where(
                CandidateCredentialSkill.credential_id == credential_id
            )
        )

        return list(result.scalars().all())