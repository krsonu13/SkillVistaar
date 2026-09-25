from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_credential import (
    CandidateCredential,
    CredentialStatus,
)
from app.models.candidate_profile import CandidateProfile
from app.models.document import (
    DocumentScanStatus,
    DocumentType,
    PrivateDocument,
)
from app.models.organization import Organization
from app.models.user import User
from app.services.document_service import (
    DocumentService,
    DocumentStorageError,
    DocumentValidationError,
)


class CandidateCredentialServiceError(Exception):
    """Base error for candidate credential operations."""


class CandidateCredentialNotFoundError(CandidateCredentialServiceError):
    """Credential does not exist."""


class CandidateCredentialValidationError(CandidateCredentialServiceError):
    """Credential data is invalid."""


class CandidateCredentialAccessDeniedError(CandidateCredentialServiceError):
    """User is not allowed to perform the operation."""


class CandidateCredentialService:
    """
    Service for candidate credential lifecycle management.

    Credential files are stored exclusively through DocumentService.
    CandidateCredential stores only the relationship to the private
    document and its credential metadata.
    """

    @staticmethod
    async def get_candidate_profile(
        db: AsyncSession,
        user: User,
    ) -> CandidateProfile:
        result = await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.user_id == user.id
            )
        )

        profile = result.scalar_one_or_none()

        if profile is None:
            raise CandidateCredentialValidationError(
                "Candidate profile not found."
            )

        return profile

    @staticmethod
    async def get_credential(
        db: AsyncSession,
        credential_id: uuid.UUID,
    ) -> CandidateCredential:
        result = await db.execute(
            select(CandidateCredential).where(
                CandidateCredential.id == credential_id
            )
        )

        credential = result.scalar_one_or_none()

        if credential is None:
            raise CandidateCredentialNotFoundError(
                "Credential not found."
            )

        return credential

    @staticmethod
    async def validate_issuer(
        db: AsyncSession,
        issuing_organization_id: uuid.UUID | None,
    ) -> Organization | None:
        if issuing_organization_id is None:
            return None

        result = await db.execute(
            select(Organization).where(
                Organization.id == issuing_organization_id,
                Organization.is_active.is_(True),
            )
        )

        organization = result.scalar_one_or_none()

        if organization is None:
            raise CandidateCredentialValidationError(
                "Issuing organization not found or inactive."
            )

        return organization

    @staticmethod
    async def validate_document(
        document: UploadFile,
    ) -> bytes:
        """
        Read the uploaded file.

        Detailed filename, MIME type, extension and size validation is
        ultimately enforced by DocumentService. This method only handles
        safe reading and the empty-file case before passing the content
        onward.
        """
        try:
            content = await document.read()
        except Exception as exc:
            raise CandidateCredentialValidationError(
                "Unable to read the uploaded document."
            ) from exc

        if not content:
            raise CandidateCredentialValidationError(
                "Uploaded document is empty."
            )

        return content

    @staticmethod
    async def check_duplicate_hash(
        db: AsyncSession,
        document_hash: str,
    ) -> bool:
        """
        Check whether this document has already been used by a credential.

        The canonical hash is now stored on PrivateDocument.
        """
        result = await db.execute(
            select(PrivateDocument.id)
            .where(
                PrivateDocument.sha256_hash == document_hash,
                PrivateDocument.document_type
                == DocumentType.CREDENTIAL.value,
            )
            .limit(1)
        )

        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_credential_document(
        db: AsyncSession,
        credential: CandidateCredential,
    ) -> PrivateDocument:
        """
        Resolve the private document linked to a credential.
        """
        if credential.document_id is None:
            raise CandidateCredentialValidationError(
                "This credential does not have a linked document."
            )

        result = await db.execute(
            select(PrivateDocument).where(
                PrivateDocument.id == credential.document_id,
            )
        )

        document = result.scalar_one_or_none()

        if document is None:
            raise CandidateCredentialValidationError(
                "The credential's document could not be found."
            )

        return document

    @classmethod
    async def create_candidate_credential(
        cls,
        db: AsyncSession,
        current_user: User,
        *,
        title: str,
        credential_type: str,
        issuing_organization_name: str,
        issuing_organization_id: uuid.UUID | None,
        credential_number: str | None,
        issue_date,
        expiry_date,
        document: UploadFile,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> CandidateCredential:
        profile = await cls.get_candidate_profile(
            db=db,
            user=current_user,
        )

        if not title or not title.strip():
            raise CandidateCredentialValidationError(
                "Credential title is required."
            )

        if not credential_type or not credential_type.strip():
            raise CandidateCredentialValidationError(
                "Credential type is required."
            )

        if (
            not issuing_organization_name
            or not issuing_organization_name.strip()
        ):
            raise CandidateCredentialValidationError(
                "Issuing organization name is required."
            )

        if issue_date and expiry_date and expiry_date < issue_date:
            raise CandidateCredentialValidationError(
                "Expiry date cannot be earlier than issue date."
            )

        normalized_credential_type = credential_type.strip().upper()

        allowed_credential_types = {
            "CERTIFICATE",
            "DIPLOMA",
            "DEGREE",
            "LICENSE",
            "TRAINING_CERTIFICATE",
            "OTHER",
        }

        if normalized_credential_type not in allowed_credential_types:
            raise CandidateCredentialValidationError(
                "Invalid credential type."
            )

        await cls.validate_issuer(
            db=db,
            issuing_organization_id=issuing_organization_id,
        )

        content = await cls.validate_document(document)

        filename = document.filename or ""
        mime_type = document.content_type or ""

        # Validate the file before creating any database record.
        document_service = DocumentService(db)

        try:
            document_service.validate_file(
                filename=filename,
                mime_type=mime_type,
                file_size=len(content),
            )
        except DocumentValidationError as exc:
            raise CandidateCredentialValidationError(
                str(exc)
            ) from exc

        document_hash = document_service.calculate_hash(content)

        duplicate = await cls.check_duplicate_hash(
            db=db,
            document_hash=document_hash,
        )

        if duplicate:
            raise CandidateCredentialValidationError(
                "This document has already been uploaded."
            )

        # Store the physical file only through DocumentService.
        try:
            private_document = await document_service.create(
                owner_user_id=current_user.id,
                document_type=DocumentType.CREDENTIAL.value,
                filename=filename,
                mime_type=mime_type,
                content=content,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
        except DocumentValidationError as exc:
            raise CandidateCredentialValidationError(
                str(exc)
            ) from exc
        except DocumentStorageError as exc:
            raise CandidateCredentialServiceError(
                str(exc)
            ) from exc

        credential = CandidateCredential(
            candidate_profile_id=profile.id,
            issuing_organization_id=issuing_organization_id,
            credential_type=normalized_credential_type,
            title=title.strip(),
            credential_number=(
                credential_number.strip()
                if credential_number
                and credential_number.strip()
                else None
            ),
            issuing_organization_name=(
                issuing_organization_name.strip()
            ),
            issue_date=issue_date,
            expiry_date=expiry_date,
            document_id=private_document.id,
            # Legacy fields are retained for backward compatibility.
            # The actual canonical document is PrivateDocument.
            document_path=None,
            document_hash=private_document.sha256_hash,
            status=CredentialStatus.UPLOADED.value,
        )

        db.add(credential)

        try:
            await db.commit()
            await db.refresh(credential)
        except Exception:
            await db.rollback()

            # DocumentService has already committed the private document.
            # Do not leave an orphaned credential document behind.
            try:
                private_document.is_active = False
                await db.commit()
            except Exception:
                await db.rollback()

            raise

        return credential

    @classmethod
    async def request_credential_verification(
        cls,
        db: AsyncSession,
        current_user: User,
        credential_id: uuid.UUID,
    ) -> CandidateCredential:
        credential = await cls.get_credential(
            db=db,
            credential_id=credential_id,
        )

        profile = await cls.get_candidate_profile(
            db=db,
            user=current_user,
        )

        if credential.candidate_profile_id != profile.id:
            raise CandidateCredentialAccessDeniedError(
                "You can only request verification for your own credentials."
            )

        if credential.status == CredentialStatus.VERIFIED.value:
            raise CandidateCredentialValidationError(
                "This credential is already verified."
            )

        if credential.status == CredentialStatus.REVOKED.value:
            raise CandidateCredentialValidationError(
                "A revoked credential cannot be submitted for verification."
            )

        private_document = await cls.get_credential_document(
            db=db,
            credential=credential,
        )

        if not private_document.is_active:
            raise CandidateCredentialValidationError(
                "The credential document is inactive and cannot be submitted."
            )

        if (
            private_document.scan_status
            != DocumentScanStatus.CLEAN.value
        ):
            raise CandidateCredentialValidationError(
                "The credential document must pass the security scan before verification."
            )

        credential.status = (
            CredentialStatus.PENDING_VERIFICATION.value
        )

        credential.verification_notes = None

        await db.commit()
        await db.refresh(credential)

        return credential

    @classmethod
    async def list_candidate_credentials(
        cls,
        db: AsyncSession,
        current_user: User,
    ) -> list[CandidateCredential]:
        profile = await cls.get_candidate_profile(
            db=db,
            user=current_user,
        )

        result = await db.execute(
            select(CandidateCredential)
            .where(
                CandidateCredential.candidate_profile_id == profile.id
            )
            .order_by(
                CandidateCredential.created_at.desc()
            )
        )

        return list(result.scalars().all())