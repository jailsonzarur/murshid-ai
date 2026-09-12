"""add lecture mindmap status

Revision ID: 7a1c3e9b42d8
Revises: 46c9a88f6aa6
Create Date: 2026-09-12

"""

import sqlalchemy as sa
from alembic import op

revision = '7a1c3e9b42d8'
down_revision = '46c9a88f6aa6'
branch_labels = None
depends_on = None

MINDMAP_STATUS = sa.Enum(
    'NONE', 'REQUESTED', 'DONE', 'FAILED', name='mindmapstatus', native_enum=False
)


def upgrade() -> None:
    op.add_column(
        'lectures',
        sa.Column('mindmap_status', MINDMAP_STATUS, nullable=False, server_default='NONE'),
    )
    op.execute("UPDATE lectures SET mindmap_status = 'DONE' WHERE mindmap_data IS NOT NULL")


def downgrade() -> None:
    op.drop_column('lectures', 'mindmap_status')
