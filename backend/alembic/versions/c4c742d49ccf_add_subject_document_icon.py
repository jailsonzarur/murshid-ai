"""add subject document icon

Square crop of the cover, rendered small so the subject card strip does not
download a full-height portrait to show a 40px tile.

Revision ID: c4c742d49ccf
Revises: 49e70d944ac9
Create Date: 2026-09-06 23:27:25.024250
"""

import sqlalchemy as sa

from alembic import op

revision = 'c4c742d49ccf'
down_revision = '49e70d944ac9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('subject_documents', sa.Column('icon_key', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('subject_documents', 'icon_key')
