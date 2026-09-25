from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import VERIFY_CREDENTIALS, require_permissions
from app.db.session import get_db
from app.models.user import User
from app.services.candidate_credential_verification_service import (
    CandidateCredentialVerificationAccessDeniedError,
    CandidateCredentialVerificationNotFoundError,
    CandidateCredentialVerificationService,
    CandidateCredentialVerificationValidationError,
)

router = APIRouter(
    prefix="/candidate-credential-verification",
    tags=["Candidate Credential Verification"],
)


class CredentialVerificationRequest(BaseModel):
    organization_id: uuid.UUID
    notes: str | None = Field(
        default=None,
        max_length=2000,
    )


class CredentialRejectionRequest(BaseModel):
    organization_id: uuid.UUID
    notes: str = Field(
        min_length=1,
        max_length=2000,
    )


class CredentialMoreInformationRequest(BaseModel):
    organization_id: uuid.UUID
    notes: str = Field(
        min_length=1,
        max_length=2000,
    )


class CredentialRevocationRequest(BaseModel):
    organization_id: uuid.UUID
    notes: str = Field(
        min_length=1,
        max_length=2000,
    )


def _handle_service_error(
    exc: Exception,
) -> HTTPException:
    if isinstance(
        exc,
        CandidateCredentialVerificationNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(
        exc,
        CandidateCredentialVerificationAccessDeniedError,
    ):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(
        exc,
        CandidateCredentialVerificationValidationError,
    ):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Credential verification failed.",
    )


@router.post(
    "/{credential_id}/approve",
    status_code=status.HTTP_200_OK,
)
async def approve_credential(
    credential_id: uuid.UUID,
    payload: CredentialVerificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_permissions(VERIFY_CREDENTIALS)
    ),
):
    """
    Approve a candidate credential.

    The verification service performs the authoritative checks:
    - verifier account is active
    - verifier has credential verification permission
    - verifier is an authorized institution member
    - institution is an approved training institute
    - credential belongs to that institution
    - candidate cannot verify their own credential
    - credential is in a reviewable state
    - linked document exists, is active, and passed security scanning
    - mapped candidate skills are verified
    - verification is audit logged
    """

    try:
        credential = (
            await CandidateCredentialVerificationService.approve(
                db=db,
                credential_id=credential_id,
                verifier_user_id=current_user.id,
                organization_id=payload.organization_id,
                notes=payload.notes,
            )
        )

        return {
            "message": "Credential verified successfully.",
            "credential_id": credential.id,
            "status": credential.status,
            "verified_at": credential.verified_at,
        }

    except Exception as exc:
        raise _handle_service_error(exc) from exc


@router.post(
    "/{credential_id}/reject",
    status_code=status.HTTP_200_OK,
)
async def reject_credential(
    credential_id: uuid.UUID,
    payload: CredentialRejectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_permissions(VERIFY_CREDENTIALS)
    ),
):
    """
    Reject a candidate credential.

    A rejection requires a reason and is restricted to an authorized
    verifier belonging to the issuing institution.
    """

    try:
        credential = (
            await CandidateCredentialVerificationService.reject(
                db=db,
                credential_id=credential_id,
                verifier_user_id=current_user.id,
                organization_id=payload.organization_id,
                reason=payload.notes,
            )
        )

        return {
            "message": "Credential rejected.",
            "credential_id": credential.id,
            "status": credential.status,
        }

    except Exception as exc:
        raise _handle_service_error(exc) from exc


@router.post(
    "/{credential_id}/request-information",
    status_code=status.HTTP_200_OK,
)
async def request_more_information(
    credential_id: uuid.UUID,
    payload: CredentialMoreInformationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_permissions(VERIFY_CREDENTIALS)
    ),
):
    """
    Request additional information from the candidate.

    The credential remains in MORE_INFORMATION_REQUIRED status.
    """

    try:
        credential = (
            await CandidateCredentialVerificationService.request_more_information(
                db=db,
                credential_id=credential_id,
                verifier_user_id=current_user.id,
                organization_id=payload.organization_id,
                notes=payload.notes,
            )
        )

        return {
            "message": "Additional information requested.",
            "credential_id": credential.id,
            "status": credential.status,
        }

    except Exception as exc:
        raise _handle_service_error(exc) from exc


@router.post(
    "/{credential_id}/revoke",
    status_code=status.HTTP_200_OK,
)
async def revoke_credential(
    credential_id: uuid.UUID,
    payload: CredentialRevocationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_permissions(VERIFY_CREDENTIALS)
    ),
):
    """
    Revoke an already verified credential.

    Only an authorized verifier belonging to the issuing institution
    can revoke the credential.
    """

    try:
        credential = (
            await CandidateCredentialVerificationService.revoke_credential(
                db=db,
                credential_id=credential_id,
                verifier_user_id=current_user.id,
                organization_id=payload.organization_id,
                reason=payload.notes,
            )
        )

        return {
            "message": "Credential revoked successfully.",
            "credential_id": credential.id,
            "status": credential.status,
        }

    except Exception as exc:
        raise _handle_service_error(exc) from exc