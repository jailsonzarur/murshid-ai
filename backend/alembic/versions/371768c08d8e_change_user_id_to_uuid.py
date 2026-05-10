"""change user id to uuid

Revision ID: 371768c08d8e
Revises: 0001
Create Date: 2026-05-03 14:43:41.814888
"""

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision = "371768c08d8e"
down_revision = "0001"
branch_labels = None
depends_on = None


def _uuid_value(dialect_name: str) -> str:
    value = uuid4()
    return str(value) if dialect_name == "postgresql" else value.hex


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    users = (
        bind.execute(
            sa.text(
                """
            SELECT name, email, password, role, created_at, updated_at
            FROM users
            """
            )
        )
        .mappings()
        .all()
    )

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")

    op.create_table(
        "users_uuid",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="GUEST"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    insert_user = sa.text(
        """
        INSERT INTO users_uuid (id, name, email, password, role, created_at, updated_at)
        VALUES (:id, :name, :email, :password, :role, :created_at, :updated_at)
        """
    )
    for user in users:
        bind.execute(insert_user, {**user, "id": _uuid_value(dialect_name)})

    op.drop_table("users")
    op.rename_table("users_uuid", "users")
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    users = (
        bind.execute(
            sa.text(
                """
            SELECT name, email, password, role, created_at, updated_at
            FROM users
            ORDER BY created_at, email
            """
            )
        )
        .mappings()
        .all()
    )

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")

    op.create_table(
        "users_int",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="GUEST"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    insert_user = sa.text(
        """
        INSERT INTO users_int (id, name, email, password, role, created_at, updated_at)
        VALUES (:id, :name, :email, :password, :role, :created_at, :updated_at)
        """
    )
    for index, user in enumerate(users, start=1):
        bind.execute(insert_user, {**user, "id": index})

    op.drop_table("users")
    op.rename_table("users_int", "users")
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
