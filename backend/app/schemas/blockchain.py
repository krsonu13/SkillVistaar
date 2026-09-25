from pydantic import BaseModel, Field


class CredentialProofRequest(BaseModel):
    credential_id: str
    document_hash: str
    institution_id: str
    status: str = Field(
        default="VERIFIED",
        max_length=30,
    )


class CredentialProofResponse(BaseModel):
    success: bool
    mode: str
    network: str
    proof_hash: str
    transaction_hash: str
    message: str