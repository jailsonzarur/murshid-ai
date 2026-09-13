"""enable pgvector

Revision ID: 9c2f5d81be74
Revises: 7a1c3e9b42d8
Create Date: 2026-09-13

"""

from alembic import op

revision = '9c2f5d81be74'
down_revision = '7a1c3e9b42d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
