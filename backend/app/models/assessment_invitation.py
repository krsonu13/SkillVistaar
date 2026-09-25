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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssessmentInvitationStatus(str, Enum):
    INVITED = "INVITED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class AssessmentInvitation(Base):
    __tablename__ = "assessment_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )

    job_application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
    )

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=AssessmentInvitationStatus.INVITED.value,
        nullable=False,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    assessment = relationship(
        "Assessment",
        backref="invitations",
    )

    job_application = relationship(
        "JobApplication",
        backref="assessment_invitations",
    )

    candidate_profile = relationship(
        "CandidateProfile",
        backref="assessment_invitations",
    )

    invited_by_user = relationship(
        "User",
        foreign_keys=[invited_by_user_id],
        backref="sent_assessment_invitations",
    )

    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "job_application_id",
            name="uq_assessment_invitation_assessment_application",
        ),
        Index(
            "ix_assessment_invitations_assessment_status",
            "assessment_id",
            "status",
        ),
        Index(
            "ix_assessment_invitations_candidate_status",
            "candidate_profile_id",
            "status",
        ),
        Index(
            "ix_assessment_invitations_application_status",
            "job_application_id",
            "status",
        ),
        Index(
            "ix_assessment_invitations_expires_at",
            "expires_at",
        ),
    )