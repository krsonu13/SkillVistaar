"""link candidate credentials to private documents

Revision ID: e376899661ed
Revises: 2e3bbd6c14a2
Create Date: 2026-09-14 23:02:42.372735

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e376899661ed"
down_revision: Union[str, Sequence[str], None] = "2e3bbd6c14a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the secure document reference to candidate credentials."""

    op.add_column(
        "candidate_credentials",
        sa.Column(
            "document_id",
            sa.UUID(),
            nullable=True,
        ),
    )

    op.alter_column(
        "candidate_credentials",
        "document_path",
        existing_type=sa.VARCHAR(length=500),
        nullable=True,
    )

    op.create_index(
        "ix_candidate_credentials_document",
        "candidate_credentials",
        ["document_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_candidate_credentials_document_id",
        "candidate_credentials",
        "private_documents",
        ["document_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove the secure document reference."""

    op.drop_constraint(
        "fk_candidate_credentials_document_id",
        "candidate_credentials",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_candidate_credentials_document",
        table_name="candidate_credentials",
    )

    op.alter_column(
        "candidate_credentials",
        "document_path",
        existing_type=sa.VARCHAR(length=500),
        nullable=False,
    )

    op.drop_column(
        "candidate_credentials",
        "document_id",
    )