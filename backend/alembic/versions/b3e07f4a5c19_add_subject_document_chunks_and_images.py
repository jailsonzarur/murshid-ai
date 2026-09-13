"""add subject document chunks and images

Revision ID: b3e07f4a5c19
Revises: 9c2f5d81be74
Create Date: 2026-09-13

"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision = 'b3e07f4a5c19'
down_revision = '9c2f5d81be74'
branch_labels = None
depends_on = None

INDEX_STATUS = sa.Enum(
    'NONE', 'REQUESTED', 'PROCESSING', 'DONE', 'FAILED',
    name='subjectdocumentindexstatus',
    native_enum=False,
)

EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    op.add_column(
        'subject_documents',
        sa.Column('index_status', INDEX_STATUS, nullable=False, server_default='NONE'),
    )
    op.add_column('subject_documents', sa.Column('chunk_count', sa.Integer(), nullable=True))

    op.create_table(
        'subject_document_chunks',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('document_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('subject_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('heading_path', sa.Text(), nullable=False),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.Column('embedding', Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['subject_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'document_id', 'sequence', name='uq_subject_document_chunks_document_sequence'
        ),
    )
    op.create_index(
        'ix_subject_document_chunks_subject_id', 'subject_document_chunks', ['subject_id']
    )
    op.execute(
        'CREATE INDEX ix_subject_document_chunks_embedding '
        'ON subject_document_chunks USING hnsw (embedding vector_cosine_ops)'
    )

    op.create_table(
        'subject_document_images',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('document_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('chunk_id', sa.Uuid(as_uuid=True), nullable=True),
        sa.Column('page', sa.Integer(), nullable=False),
        sa.Column('bbox', JSONB(), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['subject_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chunk_id'], ['subject_document_chunks.id'], ondelete='SET NULL'),
    )
    op.create_index(
        'ix_subject_document_images_document_id', 'subject_document_images', ['document_id']
    )
    op.create_index('ix_subject_document_images_chunk_id', 'subject_document_images', ['chunk_id'])


def downgrade() -> None:
    op.drop_table('subject_document_images')
    op.drop_table('subject_document_chunks')
    op.drop_column('subject_documents', 'chunk_count')
    op.drop_column('subject_documents', 'index_status')
