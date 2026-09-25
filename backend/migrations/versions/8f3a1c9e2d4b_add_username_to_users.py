"""add username to users

Revision ID: 8f3a1c9e2d4b
Revises: fe729b8c4d12
Create Date: 2026-09-23 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8f3a1c9e2d4b'
down_revision: Union[str, Sequence[str], None] = 'bd81be145379'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('users')]
    if 'username' not in cols:
        op.add_column('users', sa.Column('username', sa.String(length=30), nullable=True))
    
    indexes = [idx['name'] for idx in insp.get_indexes('users')]
    if 'ix_users_username' not in indexes:
        op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    if 'ix_users_username_lower' not in indexes:
        op.create_index('ix_users_username_lower', 'users', [sa.text('lower(username)')], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    indexes = [idx['name'] for idx in insp.get_indexes('users')]
    if 'ix_users_username_lower' in indexes:
        op.drop_index('ix_users_username_lower', table_name='users')
    if 'ix_users_username' in indexes:
        op.drop_index(op.f('ix_users_username'), table_name='users')
    cols = [c['name'] for c in insp.get_columns('users')]
    if 'username' in cols:
        op.drop_column('users', 'username')
