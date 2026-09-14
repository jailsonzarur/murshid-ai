"""add lecture guided summary

Revision ID: c1a84f39d206
Revises: b3e07f4a5c19
Create Date: 2026-09-14

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = 'c1a84f39d206'
down_revision = 'b3e07f4a5c19'
branch_labels = None
depends_on = None

GUIDED_STATUS = sa.Enum(
    'NONE', 'REQUESTED', 'PROCESSING', 'DONE', 'FAILED',
    name='guidedsummarystatus',
    native_enum=False,
)


def upgrade() -> None:
    op.add_column('lectures', sa.Column('guided_summary', sa.Text(), nullable=True))
    op.add_column(
        'lectures',
        sa.Column('guided_status', GUIDED_STATUS, nullable=False, server_default='NONE'),
    )

    op.create_table(
        'lecture_guided_citations',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('lecture_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('topic', sa.Text(), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('results', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['lecture_id'], ['lectures.id'], ondelete='CASCADE'),
    )
    op.create_index(
        'ix_lecture_guided_citations_lecture_id', 'lecture_guided_citations', ['lecture_id']
    )


def downgrade() -> None:
    op.drop_table('lecture_guided_citations')
    op.drop_column('lectures', 'guided_status')
    op.drop_column('lectures', 'guided_summary')
