"""align_remaining_models

Revision ID: bd81be145379
Revises: fe729b8c4d12
Create Date: 2026-09-22 22:48:38.845052

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'bd81be145379'
down_revision: Union[str, Sequence[str], None] = 'fe729b8c4d12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    # 1. signup_verification_sessions
    if 'signup_verification_sessions' not in tables:
        op.create_table(
            'signup_verification_sessions',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('session_token', sa.String(length=255), nullable=False),
            sa.Column('account_type', sa.String(length=50), nullable=False),
            sa.Column('primary_channel', sa.String(length=20), nullable=False),
            sa.Column('primary_identifier', sa.String(length=255), nullable=False),
            sa.Column('primary_code_hash', sa.String(length=255), nullable=False),
            sa.Column('primary_verified', sa.Boolean(), nullable=False),
            sa.Column('primary_verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('secondary_channel', sa.String(length=20), nullable=True),
            sa.Column('secondary_identifier', sa.String(length=255), nullable=True),
            sa.Column('secondary_code_hash', sa.String(length=255), nullable=True),
            sa.Column('secondary_verified', sa.Boolean(), nullable=False),
            sa.Column('secondary_verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('attempts', sa.Integer(), nullable=False),
            sa.Column('max_attempts', sa.Integer(), nullable=False),
            sa.Column('completed', sa.Boolean(), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_signup_sessions_expires_at', 'signup_verification_sessions', ['expires_at'], unique=False)
        op.create_index('ix_signup_sessions_token_completed', 'signup_verification_sessions', ['session_token', 'completed'], unique=False)
        op.create_index(op.f('ix_signup_verification_sessions_session_token'), 'signup_verification_sessions', ['session_token'], unique=True)

    # 2. organization_documents
    if 'organization_documents' not in tables:
        op.create_table(
            'organization_documents',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('organization_id', sa.UUID(), nullable=False),
            sa.Column('document_id', sa.UUID(), nullable=True),
            sa.Column('document_type', sa.String(length=80), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('document_number', sa.String(length=100), nullable=True),
            sa.Column('issuing_authority', sa.String(length=255), nullable=True),
            sa.Column('issue_date', sa.Date(), nullable=True),
            sa.Column('expiry_date', sa.Date(), nullable=True),
            sa.Column('file_name', sa.String(length=255), nullable=True),
            sa.Column('file_url', sa.String(length=500), nullable=True),
            sa.Column('file_size', sa.Integer(), nullable=True),
            sa.Column('mime_type', sa.String(length=100), nullable=True),
            sa.Column('status', sa.String(length=40), server_default='PENDING', nullable=False),
            sa.Column('uploaded_by_user_id', sa.UUID(), nullable=False),
            sa.Column('verifier_user_id', sa.UUID(), nullable=True),
            sa.Column('verification_remarks', sa.Text(), nullable=True),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['document_id'], ['private_documents.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='RESTRICT'),
            sa.ForeignKeyConstraint(['verifier_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_org_docs_expiry', 'organization_documents', ['expiry_date'], unique=False)
        op.create_index('ix_org_docs_org_id', 'organization_documents', ['organization_id'], unique=False)
        op.create_index('ix_org_docs_status', 'organization_documents', ['status'], unique=False)
        op.create_index('ix_org_docs_type', 'organization_documents', ['document_type'], unique=False)

    # 3. organization_document_history
    if 'organization_document_history' not in tables:
        op.create_table(
            'organization_document_history',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('document_id', sa.UUID(), nullable=False),
            sa.Column('actor_user_id', sa.UUID(), nullable=True),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('previous_status', sa.String(length=40), nullable=True),
            sa.Column('new_status', sa.String(length=40), nullable=False),
            sa.Column('remarks', sa.Text(), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['document_id'], ['organization_documents.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_org_doc_hist_created_at', 'organization_document_history', ['created_at'], unique=False)
        op.create_index('ix_org_doc_hist_doc_id', 'organization_document_history', ['document_id'], unique=False)

    # 4. institution_profiles columns
    inst_cols = [c['name'] for c in insp.get_columns('institution_profiles')]
    for col_name, col_type in [
        ('affiliation', sa.String(length=255)),
        ('ownership_type', sa.String(length=100)),
        ('established_year', sa.Integer()),
        ('trainers', postgresql.JSONB(astext_type=sa.Text())),
        ('infrastructure', postgresql.JSONB(astext_type=sa.Text())),
        ('partnerships', postgresql.JSONB(astext_type=sa.Text())),
        ('curriculum_alignment', postgresql.JSONB(astext_type=sa.Text())),
    ]:
        if col_name not in inst_cols:
            op.add_column('institution_profiles', sa.Column(col_name, col_type, nullable=True))

    # 5. organizations columns
    org_cols = [c['name'] for c in insp.get_columns('organizations')]
    for col_name, col_type in [
        ('sector', sa.String(length=150)),
        ('company_size', sa.String(length=50)),
        ('branches', postgresql.JSONB(astext_type=sa.Text())),
        ('contact_persons', postgresql.JSONB(astext_type=sa.Text())),
        ('industry_skills', postgresql.JSONB(astext_type=sa.Text())),
    ]:
        if col_name not in org_cols:
            op.add_column('organizations', sa.Column(col_name, col_type, nullable=True))

    # 6. jobs columns
    jobs_cols = [c['name'] for c in insp.get_columns('jobs')]
    if 'role_family' not in jobs_cols:
        op.add_column('jobs', sa.Column('role_family', sa.String(length=150), nullable=True))
    if 'occupation_code' not in jobs_cols:
        op.add_column('jobs', sa.Column('occupation_code', sa.String(length=100), nullable=True))
    if 'qualification' not in jobs_cols:
        op.add_column('jobs', sa.Column('qualification', sa.Text(), nullable=True))
    if 'minimum_experience' not in jobs_cols:
        op.add_column('jobs', sa.Column('minimum_experience', sa.Float(), nullable=False, server_default='0'))
    if 'maximum_experience' not in jobs_cols:
        op.add_column('jobs', sa.Column('maximum_experience', sa.Float(), nullable=True))
    if 'district' not in jobs_cols:
        op.add_column('jobs', sa.Column('district', sa.String(length=150), nullable=True))
    if 'work_mode' not in jobs_cols:
        op.add_column('jobs', sa.Column('work_mode', sa.String(length=30), nullable=False, server_default='ON_SITE'))
    if 'salary_min' not in jobs_cols:
        op.add_column('jobs', sa.Column('salary_min', sa.Integer(), nullable=True))
    if 'salary_max' not in jobs_cols:
        op.add_column('jobs', sa.Column('salary_max', sa.Integer(), nullable=True))
    if 'shift' not in jobs_cols:
        op.add_column('jobs', sa.Column('shift', sa.String(length=100), nullable=True))
    if 'travel_required' not in jobs_cols:
        op.add_column('jobs', sa.Column('travel_required', sa.Boolean(), nullable=False, server_default='false'))
    if 'joining_timeline' not in jobs_cols:
        op.add_column('jobs', sa.Column('joining_timeline', sa.String(length=150), nullable=True))
    if 'is_public' not in jobs_cols:
        op.add_column('jobs', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'))

    # 7. job_applications columns
    app_cols = [c['name'] for c in insp.get_columns('job_applications')]
    if 'candidate_user_id' not in app_cols:
        op.add_column('job_applications', sa.Column('candidate_user_id', sa.Uuid(), nullable=True))
    if 'resume_document_id' not in app_cols:
        op.add_column('job_applications', sa.Column('resume_document_id', sa.Uuid(), nullable=True))
    if 'total_required_skills' not in app_cols:
        op.add_column('job_applications', sa.Column('total_required_skills', sa.Integer(), nullable=False, server_default='0'))
    if 'matched_preferred_skills' not in app_cols:
        op.add_column('job_applications', sa.Column('matched_preferred_skills', sa.Integer(), nullable=False, server_default='0'))
    if 'total_preferred_skills' not in app_cols:
        op.add_column('job_applications', sa.Column('total_preferred_skills', sa.Integer(), nullable=False, server_default='0'))
    if 'consent_to_share_profile' not in app_cols:
        op.add_column('job_applications', sa.Column('consent_to_share_profile', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    pass
