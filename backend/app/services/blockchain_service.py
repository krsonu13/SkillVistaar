import hashlib
import json
from typing import Any


class BlockchainServiceError(Exception):
    pass


class BlockchainService:
    """
    Blockchain trust-layer abstraction.

    PostgreSQL remains the system of record.
    Only credential proofs and verification events are intended
    to be anchored on-chain.
    """

    def __init__(self):
        self.network = "prototype-permissioned"
        self.enabled = False

    @staticmethod
    def calculate_document_hash(
        document_bytes: bytes,
    ) -> str:
        return hashlib.sha256(
            document_bytes
        ).hexdigest()

    @staticmethod
    def calculate_credential_proof(
        credential_id: str,
        document_hash: str,
        institution_id: str,
        status: str,
    ) -> str:
        payload = {
            "credential_id": credential_id,
            "document_hash": document_hash,
            "institution_id": institution_id,
            "status": status,
        }

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

    async def anchor_credential(
        self,
        credential_id: str,
        document_hash: str,
        institution_id: str,
        status: str = "VERIFIED",
    ) -> dict[str, Any]:
        proof_hash = self.calculate_credential_proof(
            credential_id=credential_id,
            document_hash=document_hash,
            institution_id=institution_id,
            status=status,
        )

        if not self.enabled:
            return {
                "success": True,
                "mode": "PROTOTYPE",
                "network": self.network,
                "proof_hash": proof_hash,
                "transaction_hash": (
                    f"prototype:{proof_hash}"
                ),
                "message": (
                    "Credential proof prepared for "
                    "permissioned blockchain anchoring."
                ),
            }

        # Real web3.py / Besu transaction will be
        # implemented when the blockchain node is connected.
        raise BlockchainServiceError(
            "Blockchain network is not configured."
        )

    async def record_revocation(
        self,
        credential_id: str,
        document_hash: str,
        institution_id: str,
    ) -> dict[str, Any]:
        return await self.anchor_credential(
            credential_id=credential_id,
            document_hash=document_hash,
            institution_id=institution_id,
            status="REVOKED",
        )