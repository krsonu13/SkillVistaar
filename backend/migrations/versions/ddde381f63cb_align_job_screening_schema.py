"""align job screening schema

Revision ID: ddde381f63cb
Revises: 9ddd32bcd857
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ddde381f63cb"
down_revision: Union[str, Sequence[str], None] = "9ddd32bcd857"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add updated_at to existing screening questions.
    #
    # The table currently contains zero rows, but the server default also
    # makes this safe if rows are introduced before this migration runs.
    op.add_column(
        "job_screening_questions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Align question_type with the application model.
    op.alter_column(
        "job_screening_questions",
        "question_type",
        existing_type=sa.String(length=40),
        type_=sa.String(length=30),
        existing_nullable=False,
    )

    # The table currently has zero rows, so converting TEXT to JSON is safe.
    # Explicit USING is required by PostgreSQL for this type conversion.
    op.alter_column(
        "job_screening_questions",
        "options",
        existing_type=sa.Text(),
        type_=sa.JSON(),
        postgresql_using="options::json",
        existing_nullable=True,
    )

    # Align created_at with the SQLAlchemy model.
    op.alter_column(
        "job_screening_questions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False,
    )

    # Support stable ordering of screening questions within a job.
    op.create_index(
        "ix_job_screening_questions_job_order",
        "job_screening_questions",
        ["job_id", "display_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_screening_questions_job_order",
        table_name="job_screening_questions",
    )

    op.alter_column(
        "job_screening_questions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

    # Convert JSON back to TEXT.
    op.alter_column(
        "job_screening_questions",
        "options",
        existing_type=sa.JSON(),
        type_=sa.Text(),
        postgresql_using="options::text",
        existing_nullable=True,
    )

    op.alter_column(
        "job_screening_questions",
        "question_type",
        existing_type=sa.String(length=30),
        type_=sa.String(length=40),
        existing_nullable=False,
    )

    op.drop_column(
        "job_screening_questions",
        "updated_at",
    )