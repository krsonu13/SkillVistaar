"""add_messaging_and_profile_fields

Revision ID: a1b2c3d4e5f6
Revises: 8f3a1c9e2d4b
Create Date: 2026-09-23 23:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8f3a1c9e2d4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to candidate_profiles
    op.add_column('candidate_profiles', sa.Column('cover_photo_path', sa.String(length=500), nullable=True))
    op.add_column('candidate_profiles', sa.Column('education', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('candidate_profiles', sa.Column('experience', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('candidate_profiles', sa.Column('projects', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('candidate_profiles', sa.Column('certifications', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('candidate_profiles', sa.Column('courses_completed', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('candidate_profiles', sa.Column('achievements', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('candidate_profiles', sa.Column('languages', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('candidate_profiles', sa.Column('career_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 2. Add columns to organizations
    op.add_column('organizations', sa.Column('logo_path', sa.String(length=500), nullable=True))
    op.add_column('organizations', sa.Column('cover_photo_path', sa.String(length=500), nullable=True))

    # 3. Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_a_id', sa.UUID(), nullable=False),
        sa.Column('user_b_id', sa.UUID(), nullable=False),
        sa.Column('initiator_user_id', sa.UUID(), nullable=False),
        sa.Column('recipient_user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='REQUESTED', nullable=False),
        sa.Column('last_message_text', sa.Text(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['initiator_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_a_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_b_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_a_id', 'user_b_id', name='uq_conversations_user_pair'),
    )
    op.create_index('ix_conversations_user_a', 'conversations', ['user_a_id'], unique=False)
    op.create_index('ix_conversations_user_b', 'conversations', ['user_b_id'], unique=False)
    op.create_index('ix_conversations_recipient_status', 'conversations', ['recipient_user_id', 'status'], unique=False)
    op.create_index('ix_conversations_last_message_at', 'conversations', ['last_message_at'], unique=False)

    # 4. Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('sender_id', sa.UUID(), nullable=False),
        sa.Column('recipient_id', sa.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_messages_conversation_created', 'messages', ['conversation_id', 'created_at'], unique=False)
    op.create_index('ix_messages_recipient_read', 'messages', ['recipient_id', 'is_read'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_messages_recipient_read', table_name='messages')
    op.drop_index('ix_messages_conversation_created', table_name='messages')
    op.drop_table('messages')

    op.drop_index('ix_conversations_last_message_at', table_name='conversations')
    op.drop_index('ix_conversations_recipient_status', table_name='conversations')
    op.drop_index('ix_conversations_user_b', table_name='conversations')
    op.drop_index('ix_conversations_user_a', table_name='conversations')
    op.drop_table('conversations')

    op.drop_column('organizations', 'cover_photo_path')
    op.drop_column('organizations', 'logo_path')

    op.drop_column('candidate_profiles', 'career_preferences')
    op.drop_column('candidate_profiles', 'languages')
    op.drop_column('candidate_profiles', 'achievements')
    op.drop_column('candidate_profiles', 'courses_completed')
    op.drop_column('candidate_profiles', 'certifications')
    op.drop_column('candidate_profiles', 'projects')
    op.drop_column('candidate_profiles', 'experience')
    op.drop_column('candidate_profiles', 'education')
    op.drop_column('candidate_profiles', 'cover_photo_path')
