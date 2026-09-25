from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class GovernmentUnit(Base):
    """
    Recursive government/jurisdiction hierarchy.

    A government unit can have another government unit as its parent,
    allowing structures such as:

        Central
            └── State
                └── District
                    └── Local

    The hierarchy is intentionally generic and does not hard-code
    any particular country's administrative structure.
    """

    __tablename__ = "government_units"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("government_units.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    unit_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    level: Mapped[int] = mapped_column(
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    jurisdiction: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    parent: Mapped[GovernmentUnit | None] = relationship(
        "GovernmentUnit",
        remote_side=[id],
        back_populates="children",
    )

    children: Mapped[list[GovernmentUnit]] = relationship(
        "GovernmentUnit",
        back_populates="parent",
        cascade="save-update, merge",
    )

    __table_args__ = (
        Index(
            "ix_government_units_parent_active",
            "parent_id",
            "is_active",
        ),
        Index(
            "ix_government_units_type_level",
            "unit_type",
            "level",
        ),
    )