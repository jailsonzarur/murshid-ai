"""expand question objective types

Revision ID: b8f4b2a1c7d9
Revises: a71c2f4b6d10
Create Date: 2026-05-17 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "b8f4b2a1c7d9"
down_revision = "a71c2f4b6d10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.alter_column(
            "type",
            existing_type=sa.String(length=10),
            type_=sa.String(length=32),
            existing_nullable=False,
        )

    op.execute("UPDATE questions SET type = 'OBJECTIVE_SINGLE' WHERE type = 'OBJECTIVE'")


def downgrade() -> None:
    op.execute("UPDATE questions SET type = 'OBJECTIVE' WHERE type IN ('OBJECTIVE_SINGLE', 'OBJECTIVE_MULTI')")

    with op.batch_alter_table("questions") as batch_op:
        batch_op.alter_column(
            "type",
            existing_type=sa.String(length=32),
            type_=sa.String(length=10),
            existing_nullable=False,
        )
