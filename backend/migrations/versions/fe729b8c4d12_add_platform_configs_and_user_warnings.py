"""add platform configs and user warnings

Revision ID: fe729b8c4d12
Revises: efe5119accd6
Create Date: 2026-09-22 22:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fe729b8c4d12'
down_revision: Union[str, Sequence[str], None] = 'efe5119accd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Platform Configs Table
    # ------------------------------------------------------------------
    op.create_table(
        'platform_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('config_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('updated_by_user_id', sa.UUID(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_platform_configs_config_key', 'platform_configs', ['config_key'], unique=False)
    op.create_index('ix_platform_configs_key_version', 'platform_configs', ['config_key', 'version'], unique=False)
    op.create_index('ix_platform_configs_key_active', 'platform_configs', ['config_key', 'is_active'], unique=False)

    # ------------------------------------------------------------------
    # 2. User Warnings Table
    # ------------------------------------------------------------------
    op.create_table(
        'user_warnings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('admin_id', sa.UUID(), nullable=True),
        sa.Column('warning_title', sa.String(length=255), nullable=False),
        sa.Column('warning_message', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=50), server_default='NORMAL', nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_warnings_user_id', 'user_warnings', ['user_id'], unique=False)
    op.create_index('ix_user_warnings_user_id_created', 'user_warnings', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('user_warnings')
    op.drop_table('platform_configs')
