from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentType(str, Enum):
    CREDENTIAL = "CREDENTIAL"
    RESUME = "RESUME"
    PROFILE_DOCUMENT = "PROFILE_DOCUMENT"
    ORGANIZATION_DOCUMENT = "ORGANIZATION_DOCUMENT"
    VERIFICATION_DOCUMENT = "VERIFICATION_DOCUMENT"
    OTHER = "OTHER"


class DocumentScanStatus(str, Enum):
    PENDING = "PENDING"
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    FAILED = "FAILED"


class PrivateDocument(Base):
    __tablename__ = "private_documents"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    scan_status: Mapped[str] = mapped_column(
        String(30),
        default=DocumentScanStatus.PENDING.value,
        nullable=False,
    )

    is_private: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    owner = relationship(
        "User",
        backref="private_documents",
    )

    __table_args__ = (
        Index(
            "ix_private_documents_owner",
            "owner_user_id",
        ),
        Index(
            "ix_private_documents_type",
            "document_type",
        ),
        Index(
            "ix_private_documents_hash",
            "sha256_hash",
        ),
        Index(
            "ix_private_documents_scan_status",
            "scan_status",
        ),
    )