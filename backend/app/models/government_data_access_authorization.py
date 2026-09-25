from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GovernmentDataAccessLevel(str, Enum):
    VIEW = "VIEW"
    ANALYZE = "ANALYZE"
    MANAGE = "MANAGE"


class GovernmentDataAccessAuthorizationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class GovernmentDataAccessAuthorization(Base):
    """
    Explicit authorization for accessing government intelligence
    and aggregated platform data.

    Authorization is tied to a government jurisdiction and follows
    the existing recursive GovernmentUnit hierarchy.

    Example:

        Central authorization
            -> Central + descendants

        State authorization
            -> State + its districts + local units

        District authorization
            -> District + its local units

        Local authorization
            -> Local unit
    """

    __tablename__ = "government_data_access_authorizations"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    government_unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "government_units.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    access_level: Mapped[str] = mapped_column(
        String(30),
        default=GovernmentDataAccessLevel.VIEW.value,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=GovernmentDataAccessAuthorizationStatus.ACTIVE.value,
        nullable=False,
    )

    # Optional restriction to particular intelligence domains.
    # Example:
    # ["LABOUR_MARKET", "PLACEMENT", "COURSE_ALIGNMENT"]
    scope: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    granted_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reason: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
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

    user = relationship(
        "User",
        foreign_keys=[user_id],
        backref="government_data_access_authorizations",
    )

    government_unit = relationship(
        "GovernmentUnit",
        backref="data_access_authorizations",
    )

    granted_by = relationship(
        "User",
        foreign_keys=[granted_by_user_id],
        backref="granted_government_data_authorizations",
    )

    __table_args__ = (
        Index(
            "ix_gov_data_access_user",
            "user_id",
        ),
        Index(
            "ix_gov_data_access_unit",
            "government_unit_id",
        ),
        Index(
            "ix_gov_data_access_status",
            "status",
        ),
        Index(
            "ix_gov_data_access_user_status",
            "user_id",
            "status",
        ),
        Index(
            "ix_gov_data_access_unit_status",
            "government_unit_id",
            "status",
        ),
    )