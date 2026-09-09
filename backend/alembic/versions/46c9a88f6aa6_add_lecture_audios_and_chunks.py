"""add lecture audios and chunks

Until now the only record that an import was in flight lived in the Celery
message: dispatch_import_lecture passed the files as a list of dicts. When the
worker died the message went with it, leaving lectures stuck in PROCESSING with
nothing to reconcile against.

These two tables make that state durable, and the unique on
(audio_id, sequence) is what lets a chunk be transcribed at most once no matter
how many times its task runs.

Revision ID: 46c9a88f6aa6
Revises: 50f62533c526
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa


revision = '46c9a88f6aa6'
down_revision = '50f62533c526'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('lecture_audios',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('lecture_id', sa.Uuid(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('object_key', sa.String(length=500), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('duration_seconds', sa.Float(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'CHUNKING', 'TRANSCRIBING', 'CONSOLIDATING', 'DONE', 'FAILED', name='lectureaudiostatus', native_enum=False), nullable=False),
    sa.Column('transcribed_seconds', sa.Float(), nullable=False),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['lecture_id'], ['lectures.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('lecture_id', 'sequence', name='uq_lecture_audios_lecture_id_sequence')
    )
    op.create_index(op.f('ix_lecture_audios_lecture_id'), 'lecture_audios', ['lecture_id'], unique=False)
    op.create_table('lecture_audio_chunks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('audio_id', sa.Uuid(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('object_key', sa.String(length=500), nullable=False),
    sa.Column('start_seconds', sa.Float(), nullable=False),
    sa.Column('duration_seconds', sa.Float(), nullable=False),
    sa.Column('transcript', sa.Text(), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['audio_id'], ['lecture_audios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('audio_id', 'sequence', name='uq_lecture_audio_chunks_audio_id_sequence')
    )
    op.create_index(op.f('ix_lecture_audio_chunks_audio_id'), 'lecture_audio_chunks', ['audio_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lecture_audio_chunks_audio_id'), table_name='lecture_audio_chunks')
    op.drop_table('lecture_audio_chunks')
    op.drop_index(op.f('ix_lecture_audios_lecture_id'), table_name='lecture_audios')
    op.drop_table('lecture_audios')
