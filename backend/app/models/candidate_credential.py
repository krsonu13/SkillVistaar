from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.document import PrivateDocument


class CredentialStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    MORE_INFORMATION_REQUIRED = "MORE_INFORMATION_REQUIRED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class CredentialType(str, Enum):
    CERTIFICATE = "CERTIFICATE"
    DIPLOMA = "DIPLOMA"
    DEGREE = "DEGREE"
    LICENSE = "LICENSE"
    TRAINING_CERTIFICATE = "TRAINING_CERTIFICATE"
    OTHER = "OTHER"


class CandidateCredential(Base):
    __tablename__ = "candidate_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    issuing_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )

    credential_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=CredentialType.CERTIFICATE.value,
        server_default=CredentialType.CERTIFICATE.value,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    credential_number: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    issuing_organization_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    issue_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expiry_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "private_documents.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    # Legacy fields retained for migration compatibility.
    document_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    document_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=CredentialStatus.UPLOADED.value,
        server_default=CredentialStatus.UPLOADED.value,
    )

    verification_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    blockchain_transaction_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    blockchain_network: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    candidate_profile = relationship(
        "CandidateProfile",
        foreign_keys=[candidate_profile_id],
    )

    issuing_organization = relationship(
        "Organization",
        foreign_keys=[issuing_organization_id],
    )

    verified_by = relationship(
        "User",
        foreign_keys=[verified_by_user_id],
    )

    document: Mapped[PrivateDocument | None] = relationship(
        PrivateDocument,
        foreign_keys=[document_id],
    )

    __table_args__ = (
        Index(
            "ix_candidate_credentials_candidate",
            "candidate_profile_id",
        ),
        Index(
            "ix_candidate_credentials_status",
            "status",
        ),
        Index(
            "ix_candidate_credentials_issuer",
            "issuing_organization_id",
        ),
        Index(
            "ix_candidate_credentials_number",
            "credential_number",
        ),
        Index(
            "ix_candidate_credentials_hash",
            "document_hash",
        ),
        Index(
            "ix_candidate_credentials_document",
            "document_id",
        ),
    )