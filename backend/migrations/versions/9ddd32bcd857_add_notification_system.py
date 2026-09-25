"""add notification system

Revision ID: 9ddd32bcd857
Revises: faf1d19974d2
Create Date: 2026-09-15 03:04:33.347779
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9ddd32bcd857"
down_revision: Union[str, Sequence[str], None] = "faf1d19974d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the notification preference system and extend notifications."""

    # ------------------------------------------------------------------
    # User notification preferences
    # ------------------------------------------------------------------
    op.create_table(
        "user_notification_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("notification_type", sa.String(length=60), nullable=False),
        sa.Column("preference", sa.String(length=30), nullable=False),
        sa.Column("enabled_email", sa.Boolean(), nullable=False),
        sa.Column("enabled_sms", sa.Boolean(), nullable=False),
        sa.Column("enabled_push", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "notification_type",
            name="uq_user_notification_preference",
        ),
    )

    # ------------------------------------------------------------------
    # Existing notifications table
    #
    # IMPORTANT:
    # Existing columns such as channel/reference_id/reference_type are
    # intentionally preserved. They may contain existing data and can be
    # removed later in a dedicated cleanup migration.
    # ------------------------------------------------------------------

    op.add_column(
        "notifications",
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=True,
        ),
    )

    op.add_column(
        "notifications",
        sa.Column(
            "translation_key",
            sa.String(length=150),
            nullable=True,
        ),
    )

    op.add_column(
        "notifications",
        sa.Column(
            "translation_params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.add_column(
        "notifications",
        sa.Column(
            "entity_type",
            sa.String(length=80),
            nullable=True,
        ),
    )

    op.add_column(
        "notifications",
        sa.Column(
            "entity_id",
            sa.UUID(),
            nullable=True,
        ),
    )

    op.add_column(
        "notifications",
        sa.Column(
            "action_url",
            sa.String(length=500),
            nullable=True,
        ),
    )

    # Existing rows need a valid priority before the column becomes NOT NULL.
    op.execute(
        "UPDATE notifications "
        "SET priority = 'NORMAL' "
        "WHERE priority IS NULL"
    )

    op.alter_column(
        "notifications",
        "priority",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default=sa.text("'NORMAL'"),
    )

    # Expand notification type length without touching existing values.
    op.alter_column(
        "notifications",
        "notification_type",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=60),
        existing_nullable=False,
    )

    # Add the indexes needed by the new notification model.
    op.create_index(
        "ix_notifications_entity",
        "notifications",
        ["entity_type", "entity_id"],
        unique=False,
    )

    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "is_read"],
        unique=False,
    )


def downgrade() -> None:
    """Reverse the notification-system changes."""

    op.drop_index(
        "ix_notifications_user_unread",
        table_name="notifications",
    )

    op.drop_index(
        "ix_notifications_entity",
        table_name="notifications",
    )

    op.alter_column(
        "notifications",
        "notification_type",
        existing_type=sa.String(length=60),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )

    op.drop_column("notifications", "action_url")
    op.drop_column("notifications", "entity_id")
    op.drop_column("notifications", "entity_type")
    op.drop_column("notifications", "translation_params")
    op.drop_column("notifications", "translation_key")
    op.drop_column("notifications", "priority")

    op.drop_table("user_notification_preferences")
