from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class OrgDocumentType(str, Enum):
    REGISTRATION_CERTIFICATE = "REGISTRATION_CERTIFICATE"
    GOVERNMENT_APPROVAL = "GOVERNMENT_APPROVAL"
    ACCREDITATION_DOCUMENT = "ACCREDITATION_DOCUMENT"
    AFFILIATION_CERTIFICATE = "AFFILIATION_CERTIFICATE"
    PAN_GST_REGISTRATION = "PAN_GST_REGISTRATION"
    ADDRESS_PROOF = "ADDRESS_PROOF"
    LICENSE_CERTIFICATE = "LICENSE_CERTIFICATE"
    AUTHORIZATION_DOCUMENT = "AUTHORIZATION_DOCUMENT"
    INSTITUTE_CERTIFICATE = "INSTITUTE_CERTIFICATE"
    INFRASTRUCTURE_AUDIT = "INFRASTRUCTURE_AUDIT"
    OTHER = "OTHER"


class OrgDocumentStatus(str, Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class OrganizationDocument(Base):
    __tablename__ = "organization_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("private_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    document_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default=OrgDocumentType.REGISTRATION_CERTIFICATE.value,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    document_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    issuing_authority: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    issue_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    expiry_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    file_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    file_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=OrgDocumentStatus.PENDING.value,
        server_default=OrgDocumentStatus.PENDING.value,
    )

    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    verifier_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    verification_remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    # Relationships
    organization = relationship(
        "Organization",
        backref="documents",
    )

    uploaded_by = relationship(
        "User",
        foreign_keys=[uploaded_by_user_id],
    )

    verifier = relationship(
        "User",
        foreign_keys=[verifier_user_id],
    )

    history = relationship(
        "OrganizationDocumentHistory",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="OrganizationDocumentHistory.created_at.desc()",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_org_docs_org_id", "organization_id"),
        Index("ix_org_docs_status", "status"),
        Index("ix_org_docs_type", "document_type"),
        Index("ix_org_docs_expiry", "expiry_date"),
    )


class OrganizationDocumentHistory(Base):
    __tablename__ = "organization_document_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization_documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    previous_status: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    new_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document = relationship(
        "OrganizationDocument",
        back_populates="history",
    )

    actor = relationship(
        "User",
        foreign_keys=[actor_user_id],
    )

    __table_args__ = (
        Index("ix_org_doc_hist_doc_id", "document_id"),
        Index("ix_org_doc_hist_created_at", "created_at"),
    )
