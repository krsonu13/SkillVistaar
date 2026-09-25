"""add_following_unique_index

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-09-24 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'uq_followings_user_target_id',
        'followings',
        ['user_id', 'target_type', 'target_id'],
        unique=True,
        postgresql_where=sa.text('target_id IS NOT NULL'),
    )
    op.create_index(
        'uq_followings_user_target_key',
        'followings',
        ['user_id', 'target_type', 'target_key'],
        unique=True,
        postgresql_where=sa.text('target_key IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_followings_user_target_key', table_name='followings')
    op.drop_index('uq_followings_user_target_id', table_name='followings')
