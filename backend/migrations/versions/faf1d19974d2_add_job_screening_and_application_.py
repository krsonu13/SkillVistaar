"""add job screening and application history

Revision ID: faf1d19974d2
Revises: e376899661ed
Create Date: 2026-09-15 00:15:44.628966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'faf1d19974d2'
down_revision: Union[str, Sequence[str], None] = 'e376899661ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add screening questions and application status history."""
    # ------------------------------------------------------------------
    # 1. Add created_by_user_id to jobs (if not already present)
    # ------------------------------------------------------------------
    op.add_column('jobs', sa.Column('created_by_user_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_jobs_created_by_user_id_users',
        'jobs',
        'users',
        ['created_by_user_id'],
        ['id'],
        ondelete='RESTRICT',
    )

    # ------------------------------------------------------------------
    # 2. Job screening questions table
    # ------------------------------------------------------------------
    op.create_table(
        'job_screening_questions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=40), nullable=False),
        sa.Column('options', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_job_screening_questions_job_id', 'job_screening_questions', ['job_id'], unique=False)

    # ------------------------------------------------------------------
    # 3. Application status history table
    # ------------------------------------------------------------------
    op.create_table(
        'application_status_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('old_status', sa.String(length=40), nullable=True),
        sa.Column('new_status', sa.String(length=40), nullable=False),
        sa.Column('changed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['job_applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_application_status_history_application_id', 'application_status_history', ['application_id'], unique=False)
    op.create_index('ix_application_status_history_created_at', 'application_status_history', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('application_status_history')
    op.drop_table('job_screening_questions')
    op.drop_constraint('fk_jobs_created_by_user_id_users', 'jobs', type_='foreignkey')
    op.drop_column('jobs', 'created_by_user_id')
