from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CandidateCredentialSkill(Base):
    __tablename__ = "candidate_credential_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    credential_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "candidate_credentials.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "skills.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    is_primary: Mapped[bool] = mapped_column(
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

    credential = relationship(
        "CandidateCredential",
        backref="skill_mappings",
    )

    skill = relationship(
        "Skill",
        backref="credential_mappings",
    )

    __table_args__ = (
        UniqueConstraint(
            "credential_id",
            "skill_id",
            name="uq_candidate_credential_skill",
        ),
        Index(
            "ix_candidate_credential_skills_credential",
            "credential_id",
        ),
        Index(
            "ix_candidate_credential_skills_skill",
            "skill_id",
        ),
    )