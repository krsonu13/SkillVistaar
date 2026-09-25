from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.blockchain import (
    CredentialProofRequest,
    CredentialProofResponse,
)
from app.services.blockchain_service import (
    BlockchainService,
    BlockchainServiceError,
)

router = APIRouter(
    prefix="/blockchain",
    tags=["Blockchain"],
)


@router.post(
    "/credential-proof",
    response_model=CredentialProofResponse,
)
async def create_credential_proof(
    data: CredentialProofRequest,
    user: User = Depends(get_current_user),
):
    """
    Prepare a credential proof for blockchain anchoring.

    This endpoint does not expose or store the actual
    certificate document on-chain.
    """

    service = BlockchainService()

    try:
        return await service.anchor_credential(
            credential_id=data.credential_id,
            document_hash=data.document_hash,
            institution_id=data.institution_id,
            status=data.status,
        )
    except BlockchainServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.post(
    "/credential-revocation",
    response_model=CredentialProofResponse,
)
async def revoke_credential_proof(
    data: CredentialProofRequest,
    user: User = Depends(get_current_user),
):
    service = BlockchainService()

    try:
        return await service.record_revocation(
            credential_id=data.credential_id,
            document_hash=data.document_hash,
            institution_id=data.institution_id,
        )
    except BlockchainServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc