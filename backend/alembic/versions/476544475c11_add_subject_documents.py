"""add subject documents

Documents attached to a subject: the base for the RAG-backed guided summary.
Uploaded files live in MinIO; only metadata is stored here.

Revision ID: 476544475c11
Revises: 3f1a90b7c204
Create Date: 2026-09-06 20:06:04.152236
"""

import sqlalchemy as sa

from alembic import op

revision = '476544475c11'
down_revision = '3f1a90b7c204'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('subject_documents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('subject_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('original_name', sa.String(length=255), nullable=False),
    sa.Column('object_key', sa.String(length=500), nullable=False),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('page_count', sa.Integer(), nullable=True),
    sa.Column(
        'status',
        sa.Enum('PENDING', 'PROCESSING', 'READY', 'FAILED', name='subjectdocumentstatus', native_enum=False),
        nullable=False,
    ),
    sa.Column('error_log', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subject_documents_subject_id'), 'subject_documents', ['subject_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subject_documents_subject_id'), table_name='subject_documents')
    op.drop_table('subject_documents')
