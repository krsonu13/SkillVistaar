from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auth_session import AuthSession
    from app.models.government_unit import GovernmentUnit
    from app.models.user_role import UserRole
    from app.models.verification_application import VerificationApplication
    from app.models.verification_challenge import VerificationChallenge


class User(Base):
    """
    Core identity/account for SkillVistaar.

    Account type and authorization roles are intentionally separate.
    A user can therefore have one primary account type while holding
    multiple authorization roles.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        unique=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        unique=True,
    )

    username: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    account_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    government_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("government_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    is_suspended: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    mfa_secret: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    password_changed_at: Mapped[datetime | None] = mapped_column(
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

    # ---------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    verification_challenges: Mapped[
        list["VerificationChallenge"]
    ] = relationship(
        "VerificationChallenge",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Applications submitted by this user.
    verification_applications: Mapped[
        list["VerificationApplication"]
    ] = relationship(
        "VerificationApplication",
        foreign_keys="VerificationApplication.applicant_user_id",
        back_populates="applicant",
        cascade="all, delete-orphan",
    )

    # Applications reviewed by this user.
    verification_reviews: Mapped[
        list["VerificationApplication"]
    ] = relationship(
        "VerificationApplication",
        foreign_keys="VerificationApplication.verifier_user_id",
        back_populates="verifier",
    )

    government_unit: Mapped[GovernmentUnit | None] = relationship(
        "GovernmentUnit",
        foreign_keys=[government_unit_id],
    )

    # ---------------------------------------------------------
    # Table indexes
    # ---------------------------------------------------------

    __table_args__ = (
        Index(
            "ix_users_account_type_active",
            "account_type",
            "is_active",
        ),
        Index(
            "ix_users_verification_status",
            "email_verified",
            "phone_verified",
        ),
        Index(
            "ix_users_security_status",
            "is_active",
            "is_suspended",
            "locked_until",
        ),
        Index(
            "ix_users_username_lower",
            func.lower(username),
            unique=True,
        ),
    )