"""create candidate profiles

Revision ID: REPLACE_REVISION
Revises: 58e59c2e2eaa
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f34be9c3c06e"
down_revision: str | None = "58e59c2e2eaa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "government_unit_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "first_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "middle_name",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "last_name",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "date_of_birth",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "gender",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "headline",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "bio",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "current_occupation",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "years_of_experience",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "highest_qualification",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "preferred_location",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "preferred_job_type",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "preferred_workplace_type",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "profile_photo_path",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "resume_path",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "profile_completion_percentage",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="INCOMPLETE",
        ),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["government_unit_id"],
            ["government_units.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_index(
        "ix_candidate_profiles_government_unit",
        "candidate_profiles",
        ["government_unit_id"],
    )

    op.create_index(
        "ix_candidate_profiles_status",
        "candidate_profiles",
        ["status"],
    )

    op.create_index(
        "ix_candidate_profiles_public",
        "candidate_profiles",
        ["is_public"],
    )

    op.create_index(
        "ix_candidate_profiles_occupation",
        "candidate_profiles",
        ["current_occupation"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_profiles_occupation",
        table_name="candidate_profiles",
    )

    op.drop_index(
        "ix_candidate_profiles_public",
        table_name="candidate_profiles",
    )

    op.drop_index(
        "ix_candidate_profiles_status",
        table_name="candidate_profiles",
    )

    op.drop_index(
        "ix_candidate_profiles_government_unit",
        table_name="candidate_profiles",
    )

    op.drop_table("candidate_profiles")