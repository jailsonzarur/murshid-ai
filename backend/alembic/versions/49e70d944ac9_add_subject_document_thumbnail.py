"""add subject document thumbnail

Key of the cover image the ingestion task renders from page 1 of a PDF.
Null while the document has not been processed, or when it has no cover.

Revision ID: 49e70d944ac9
Revises: 476544475c11
Create Date: 2026-09-06 22:57:56.604820
"""

import sqlalchemy as sa

from alembic import op

revision = '49e70d944ac9'
down_revision = '476544475c11'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('subject_documents', sa.Column('thumbnail_key', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('subject_documents', 'thumbnail_key')
