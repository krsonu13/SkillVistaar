from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    VERIFY_CREDENTIALS,
    get_permissions_for_roles,
)
from app.models.candidate_credential import (
    CandidateCredential,
    CredentialStatus,
)
from app.models.candidate_credential_skill import CandidateCredentialSkill
from app.models.candidate_profile import CandidateProfile
from app.models.candidate_skill import (
    CandidateSkill,
    CandidateSkillStatus,
)
from app.models.document import (
    DocumentScanStatus,
    PrivateDocument,
)
from app.models.organization import (
    Organization,
    OrganizationType,
)
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.services.audit_log_service import AuditLogService


class CandidateCredentialVerificationServiceError(Exception):
    """Base exception for credential verification operations."""


class CandidateCredentialNotFoundError(
    CandidateCredentialVerificationServiceError
):
    """Raised when a credential does not exist."""


class CandidateCredentialValidationError(
    CandidateCredentialVerificationServiceError
):
    """Raised when credential verification data is invalid."""


class CandidateCredentialAccessDeniedError(
    CandidateCredentialVerificationServiceError
):
    """Raised when a verifier is not authorized."""


# Backward-compatible aliases.
CandidateCredentialVerificationError = (
    CandidateCredentialVerificationServiceError
)

CandidateCredentialVerificationNotFoundError = (
    CandidateCredentialNotFoundError
)

CandidateCredentialVerificationValidationError = (
    CandidateCredentialValidationError
)

CandidateCredentialVerificationAccessDeniedError = (
    CandidateCredentialAccessDeniedError
)

CredentialNotFoundError = CandidateCredentialNotFoundError
CredentialValidationError = CandidateCredentialValidationError
CredentialAccessDeniedError = CandidateCredentialAccessDeniedError


class CandidateCredentialVerificationService:
    """Business logic for institution-side credential verification."""

    INSTITUTION_VERIFIER_ROLES = {
        "ORG_ADMIN",
        "INSTITUTION_ADMIN",
    }

    REVIEWABLE_STATUSES = {
        CredentialStatus.UPLOADED.value,
        CredentialStatus.PENDING_VERIFICATION.value,
        CredentialStatus.MORE_INFORMATION_REQUIRED.value,
    }

    @staticmethod
    async def _get_user_roles(
        db: AsyncSession,
        user_id: UUID,
    ) -> set[str]:
        result = await db.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                UserRole.is_active.is_(True),
                Role.is_active.is_(True),
            )
        )

        return set(result.scalars().all())

    @classmethod
    async def ensure_institution_verifier(
        cls,
        db: AsyncSession,
        user_id: UUID,
        organization_id: UUID,
    ) -> tuple[User, Organization, OrganizationMember]:
        user = await db.get(User, user_id)

        if user is None:
            raise CandidateCredentialAccessDeniedError(
                "Verifier account was not found."
            )

        if not user.is_active or getattr(user, "is_suspended", False):
            raise CandidateCredentialAccessDeniedError(
                "Verifier account is inactive or suspended."
            )

        organization = await db.get(
            Organization,
            organization_id,
        )

        if organization is None or not organization.is_active:
            raise CandidateCredentialAccessDeniedError(
                "Issuing institution was not found or is inactive."
            )

        if (
            organization.organization_type
            != OrganizationType.TRAINING_INSTITUTE.value
        ):
            raise CandidateCredentialAccessDeniedError(
                "Only approved training institutions can verify credentials."
            )

        if organization.verification_status != "APPROVED":
            raise CandidateCredentialAccessDeniedError(
                "The institution must be approved before it can verify credentials."
            )

        roles = await cls._get_user_roles(
            db,
            user_id,
        )

        permissions = get_permissions_for_roles(roles)

        if VERIFY_CREDENTIALS not in permissions:
            raise CandidateCredentialAccessDeniedError(
                "User does not have permission to verify credentials."
            )

        member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active.is_(True),
                OrganizationMember.role_code.in_(
                    cls.INSTITUTION_VERIFIER_ROLES
                ),
            )
        )

        member = member_result.scalar_one_or_none()

        if member is None:
            raise CandidateCredentialAccessDeniedError(
                "User is not an authorized verifier for this institution."
            )

        return user, organization, member

    @staticmethod
    async def ensure_not_candidate_verifier(
        db: AsyncSession,
        credential: CandidateCredential,
        verifier_user_id: UUID,
    ) -> None:
        candidate_profile = await db.get(
            CandidateProfile,
            credential.candidate_profile_id,
        )

        if candidate_profile is None:
            raise CandidateCredentialValidationError(
                "Candidate profile associated with the credential was not found."
            )

        if candidate_profile.user_id == verifier_user_id:
            raise CandidateCredentialAccessDeniedError(
                "A candidate cannot verify their own credential."
            )

    @classmethod
    def ensure_credential_can_be_reviewed(
        cls,
        credential: CandidateCredential,
    ) -> None:
        if credential.status not in cls.REVIEWABLE_STATUSES:
            raise CandidateCredentialValidationError(
                f"Credential cannot be reviewed while in status "
                f"{credential.status}."
            )

    @staticmethod
    async def ensure_credential_document_is_safe(
        db: AsyncSession,
        credential: CandidateCredential,
    ) -> PrivateDocument:
        """
        A credential may only be approved when its linked private
        document exists, is active, and has passed the security scan.
        """

        if credential.document_id is None:
            raise CandidateCredentialValidationError(
                "Credential cannot be verified because no document is linked."
            )

        result = await db.execute(
            select(PrivateDocument).where(
                PrivateDocument.id == credential.document_id,
            )
        )

        document = result.scalar_one_or_none()

        if document is None:
            raise CandidateCredentialValidationError(
                "Credential document could not be found."
            )

        if not document.is_active:
            raise CandidateCredentialValidationError(
                "Credential cannot be verified because its document is inactive."
            )

        if (
            document.scan_status
            != DocumentScanStatus.CLEAN.value
        ):
            raise CandidateCredentialValidationError(
                "Credential cannot be verified until its document passes the security scan."
            )

        return document

    @staticmethod
    async def verify_mapped_candidate_skills(
        db: AsyncSession,
        credential: CandidateCredential,
        verifier_user_id: UUID,
        verification_notes: str | None,
    ) -> None:
        mapping_result = await db.execute(
            select(CandidateCredentialSkill).where(
                CandidateCredentialSkill.credential_id == credential.id
            )
        )

        mappings = mapping_result.scalars().all()

        now = datetime.now(timezone.utc)

        for mapping in mappings:
            skill_result = await db.execute(
                select(CandidateSkill).where(
                    CandidateSkill.candidate_profile_id
                    == credential.candidate_profile_id,
                    CandidateSkill.skill_id == mapping.skill_id,
                )
            )

            candidate_skill = skill_result.scalar_one_or_none()

            if candidate_skill is None:
                candidate_skill = CandidateSkill(
                    candidate_profile_id=credential.candidate_profile_id,
                    skill_id=mapping.skill_id,
                    proficiency_level="INTERMEDIATE",
                    years_of_experience=0,
                    status=CandidateSkillStatus.VERIFIED.value,
                    is_primary=mapping.is_primary,
                    verified_by_user_id=verifier_user_id,
                    verified_at=now,
                    expires_at=credential.expiry_date,
                    verification_notes=verification_notes,
                )

                db.add(candidate_skill)

            else:
                candidate_skill.status = (
                    CandidateSkillStatus.VERIFIED.value
                )
                candidate_skill.verified_by_user_id = verifier_user_id
                candidate_skill.verified_at = now
                candidate_skill.expires_at = credential.expiry_date
                candidate_skill.verification_notes = verification_notes

    @staticmethod
    async def _get_verified_supporting_credentials(
        db: AsyncSession,
        credential: CandidateCredential,
        skill_id: UUID,
    ) -> list[CandidateCredential]:
        result = await db.execute(
            select(CandidateCredential)
            .join(
                CandidateCredentialSkill,
                CandidateCredentialSkill.credential_id
                == CandidateCredential.id,
            )
            .where(
                CandidateCredential.candidate_profile_id
                == credential.candidate_profile_id,
                CandidateCredentialSkill.skill_id == skill_id,
                CandidateCredential.status
                == CredentialStatus.VERIFIED.value,
                CandidateCredential.id != credential.id,
            )
        )

        return list(result.scalars().unique().all())

    @classmethod
    async def _reconcile_skills_after_credential_status_change(
        cls,
        db: AsyncSession,
        credential: CandidateCredential,
        target_status: str,
        notes: str | None,
    ) -> None:
        mapping_result = await db.execute(
            select(CandidateCredentialSkill).where(
                CandidateCredentialSkill.credential_id == credential.id
            )
        )

        mappings = mapping_result.scalars().all()

        for mapping in mappings:
            supporting_credentials = (
                await cls._get_verified_supporting_credentials(
                    db,
                    credential,
                    mapping.skill_id,
                )
            )

            if supporting_credentials:
                continue

            skill_result = await db.execute(
                select(CandidateSkill).where(
                    CandidateSkill.candidate_profile_id
                    == credential.candidate_profile_id,
                    CandidateSkill.skill_id == mapping.skill_id,
                    CandidateSkill.status
                    == CandidateSkillStatus.VERIFIED.value,
                )
            )

            candidate_skill = skill_result.scalar_one_or_none()

            if candidate_skill is None:
                continue

            candidate_skill.status = target_status
            candidate_skill.verification_notes = notes

            if target_status in {
                CandidateSkillStatus.REVOKED.value,
                CandidateSkillStatus.EXPIRED.value,
            }:
                candidate_skill.verified_at = None
                candidate_skill.verified_by_user_id = None

    @staticmethod
    async def _audit(
        db: AsyncSession,
        *,
        actor_user_id: UUID,
        action: str,
        credential: CandidateCredential,
        description: str,
        metadata: dict | None = None,
    ) -> None:
        await AuditLogService.record(
            db,
            actor_user_id=actor_user_id,
            action=action,
            resource_type="CandidateCredential",
            resource_id=credential.id,
            description=description,
            metadata=metadata,
        )

    @classmethod
    async def approve(
        cls,
        db: AsyncSession,
        credential_id: UUID,
        verifier_user_id: UUID,
        organization_id: UUID,
        notes: str | None = None,
    ) -> CandidateCredential:
        _, organization, _ = await cls.ensure_institution_verifier(
            db,
            verifier_user_id,
            organization_id,
        )

        credential = await db.get(
            CandidateCredential,
            credential_id,
        )

        if credential is None:
            raise CandidateCredentialNotFoundError(
                "Credential was not found."
            )

        if credential.issuing_organization_id != organization.id:
            raise CandidateCredentialAccessDeniedError(
                "Verifier can only verify credentials issued by their institution."
            )

        await cls.ensure_not_candidate_verifier(
            db,
            credential,
            verifier_user_id,
        )

        cls.ensure_credential_can_be_reviewed(credential)

        # Security gate:
        # A credential cannot become VERIFIED unless the linked
        # PrivateDocument exists, is active, and passed scanning.
        await cls.ensure_credential_document_is_safe(
            db,
            credential,
        )

        now = datetime.now(timezone.utc)

        credential.status = CredentialStatus.VERIFIED.value
        credential.verified_by_user_id = verifier_user_id
        credential.verified_at = now
        credential.verification_notes = notes

        await cls.verify_mapped_candidate_skills(
            db,
            credential,
            verifier_user_id,
            notes,
        )

        await cls._audit(
            db,
            actor_user_id=verifier_user_id,
            action="VERIFY",
            credential=credential,
            description="Candidate credential approved and verified.",
            metadata={
                "organization_id": str(organization.id),
                "credential_status": credential.status,
                "document_id": (
                    str(credential.document_id)
                    if credential.document_id
                    else None
                ),
                "document_scan_status": DocumentScanStatus.CLEAN.value,
            },
        )

        await db.commit()
        await db.refresh(credential)

        return credential

    @classmethod
    async def reject(
        cls,
        db: AsyncSession,
        credential_id: UUID,
        verifier_user_id: UUID,
        organization_id: UUID,
        reason: str,
    ) -> CandidateCredential:
        reason = reason.strip()

        if not reason:
            raise CandidateCredentialValidationError(
                "Rejection reason is required."
            )

        _, organization, _ = await cls.ensure_institution_verifier(
            db,
            verifier_user_id,
            organization_id,
        )

        credential = await db.get(
            CandidateCredential,
            credential_id,
        )

        if credential is None:
            raise CandidateCredentialNotFoundError(
                "Credential was not found."
            )

        if credential.issuing_organization_id != organization.id:
            raise CandidateCredentialAccessDeniedError(
                "Verifier can only review credentials issued by their institution."
            )

        await cls.ensure_not_candidate_verifier(
            db,
            credential,
            verifier_user_id,
        )

        cls.ensure_credential_can_be_reviewed(credential)

        credential.status = CredentialStatus.REJECTED.value
        credential.verified_by_user_id = None
        credential.verified_at = None
        credential.verification_notes = reason

        await cls._reconcile_skills_after_credential_status_change(
            db,
            credential,
            CandidateSkillStatus.REJECTED.value,
            reason,
        )

        await cls._audit(
            db,
            actor_user_id=verifier_user_id,
            action="REJECT",
            credential=credential,
            description="Candidate credential rejected.",
            metadata={
                "organization_id": str(organization.id),
                "reason": reason,
                "credential_status": credential.status,
            },
        )

        await db.commit()
        await db.refresh(credential)

        return credential

    @classmethod
    async def request_more_information(
        cls,
        db: AsyncSession,
        credential_id: UUID,
        verifier_user_id: UUID,
        organization_id: UUID,
        notes: str,
    ) -> CandidateCredential:
        notes = notes.strip()

        if not notes:
            raise CandidateCredentialValidationError(
                "Additional information request is required."
            )

        _, organization, _ = await cls.ensure_institution_verifier(
            db,
            verifier_user_id,
            organization_id,
        )

        credential = await db.get(
            CandidateCredential,
            credential_id,
        )

        if credential is None:
            raise CandidateCredentialNotFoundError(
                "Credential was not found."
            )

        if credential.issuing_organization_id != organization.id:
            raise CandidateCredentialAccessDeniedError(
                "Verifier can only review credentials issued by their institution."
            )

        await cls.ensure_not_candidate_verifier(
            db,
            credential,
            verifier_user_id,
        )

        cls.ensure_credential_can_be_reviewed(credential)

        credential.status = (
            CredentialStatus.MORE_INFORMATION_REQUIRED.value
        )
        credential.verification_notes = notes

        await cls._audit(
            db,
            actor_user_id=verifier_user_id,
            action="REQUEST_INFORMATION",
            credential=credential,
            description="Additional information requested for candidate credential.",
            metadata={
                "organization_id": str(organization.id),
                "credential_status": credential.status,
            },
        )

        await db.commit()
        await db.refresh(credential)

        return credential

    @classmethod
    async def revoke_credential(
        cls,
        db: AsyncSession,
        credential_id: UUID,
        verifier_user_id: UUID,
        organization_id: UUID,
        reason: str,
    ) -> CandidateCredential:
        reason = reason.strip()

        if not reason:
            raise CandidateCredentialValidationError(
                "Revocation reason is required."
            )

        _, organization, _ = await cls.ensure_institution_verifier(
            db,
            verifier_user_id,
            organization_id,
        )

        credential = await db.get(
            CandidateCredential,
            credential_id,
        )

        if credential is None:
            raise CandidateCredentialNotFoundError(
                "Credential was not found."
            )

        if credential.issuing_organization_id != organization.id:
            raise CandidateCredentialAccessDeniedError(
                "Verifier can only revoke credentials issued by their institution."
            )

        await cls.ensure_not_candidate_verifier(
            db,
            credential,
            verifier_user_id,
        )

        if credential.status != CredentialStatus.VERIFIED.value:
            raise CandidateCredentialValidationError(
                "Only a verified credential can be revoked."
            )

        credential.status = CredentialStatus.REVOKED.value
        credential.verification_notes = reason

        await cls._reconcile_skills_after_credential_status_change(
            db,
            credential,
            CandidateSkillStatus.REVOKED.value,
            reason,
        )

        await cls._audit(
            db,
            actor_user_id=verifier_user_id,
            action="REVOKE",
            credential=credential,
            description="Previously verified candidate credential revoked.",
            metadata={
                "organization_id": str(organization.id),
                "reason": reason,
                "credential_status": credential.status,
            },
        )

        await db.commit()
        await db.refresh(credential)

        return credential

    @classmethod
    async def expire_credential(
        cls,
        db: AsyncSession,
        credential_id: UUID,
    ) -> CandidateCredential:
        credential = await db.get(
            CandidateCredential,
            credential_id,
        )

        if credential is None:
            raise CandidateCredentialNotFoundError(
                "Credential was not found."
            )

        if credential.status != CredentialStatus.VERIFIED.value:
            raise CandidateCredentialValidationError(
                "Only a verified credential can expire."
            )

        if credential.expiry_date is None:
            raise CandidateCredentialValidationError(
                "Credential has no expiry date."
            )

        now = datetime.now(timezone.utc)

        if credential.expiry_date > now.date():
            raise CandidateCredentialValidationError(
                "Credential has not reached its expiry date."
            )

        credential.status = CredentialStatus.EXPIRED.value
        credential.verification_notes = "Credential expired."

        await cls._reconcile_skills_after_credential_status_change(
            db,
            credential,
            CandidateSkillStatus.EXPIRED.value,
            "Credential expired.",
        )

        # System expiration has no human actor.
        await db.commit()
        await db.refresh(credential)

        return credential

    @staticmethod
    async def get_verified_credential_skill_ids(
        db: AsyncSession,
        credential_id: UUID,
    ) -> set[UUID]:
        credential = await db.get(
            CandidateCredential,
            credential_id,
        )

        if credential is None:
            raise CandidateCredentialNotFoundError(
                "Credential was not found."
            )

        if credential.status != CredentialStatus.VERIFIED.value:
            return set()

        result = await db.execute(
            select(CandidateCredentialSkill.skill_id).where(
                CandidateCredentialSkill.credential_id == credential_id
            )
        )

        return set(result.scalars().all())