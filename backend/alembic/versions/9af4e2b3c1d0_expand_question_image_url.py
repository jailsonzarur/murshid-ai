"""expand question image url

Revision ID: 9af4e2b3c1d0
Revises: 81940abc8c98
Create Date: 2026-05-03 23:15:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "9af4e2b3c1d0"
down_revision = "81940abc8c98"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "questions",
        "image_url",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "questions",
        "image_url",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
