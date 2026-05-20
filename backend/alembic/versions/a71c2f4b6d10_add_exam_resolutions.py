"""add exam resolutions

Revision ID: a71c2f4b6d10
Revises: 9af4e2b3c1d0
Create Date: 2026-05-17 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "a71c2f4b6d10"
down_revision = "9af4e2b3c1d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("explanation", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("expected_answer", sa.Text(), nullable=True))

    op.create_table(
        "exam_resolutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "mode",
            sa.Enum("EXAM", "STUDY", name="examresolutionmode", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "IN_PROGRESS",
                "PAUSED",
                "SUBMITTED",
                "GRADED",
                "ERROR",
                name="examresolutionstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "result",
            sa.Enum("PASSED", "FAILED", name="examresolutionresult", native_enum=False),
            nullable=True,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("score IS NULL OR (score >= 0 AND score <= 1)", name="ck_exam_resolutions_score_range"),
        sa.CheckConstraint("time_spent_seconds >= 0", name="ck_exam_resolutions_time_spent_non_negative"),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exam_resolutions_exam_id"), "exam_resolutions", ["exam_id"], unique=False)
    op.create_index(op.f("ix_exam_resolutions_user_id"), "exam_resolutions", ["user_id"], unique=False)

    op.create_table(
        "question_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resolution_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["resolution_id"], ["exam_resolutions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_responses_question_id"), "question_responses", ["question_id"], unique=False)
    op.create_index(op.f("ix_question_responses_resolution_id"), "question_responses", ["resolution_id"], unique=False)

    op.create_table(
        "question_response_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=False),
        sa.Column("option_id", sa.Uuid(), nullable=True),
        sa.Column("text_answer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["option_id"], ["options.id"]),
        sa.ForeignKeyConstraint(["response_id"], ["question_responses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_question_response_items_response_id"),
        "question_response_items",
        ["response_id"],
        unique=False,
    )

    op.create_table(
        "question_response_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column(
            "evaluation_source",
            sa.Enum("AUTO", "AI", "MANUAL", name="responseevaluationsource", native_enum=False),
            nullable=False,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.CheckConstraint("score >= 0 AND score <= 1", name="ck_question_response_evaluations_score_range"),
        sa.ForeignKeyConstraint(["response_id"], ["question_responses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_question_response_evaluations_response_id"),
        "question_response_evaluations",
        ["response_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_question_response_evaluations_response_id"), table_name="question_response_evaluations")
    op.drop_table("question_response_evaluations")
    op.drop_index(op.f("ix_question_response_items_response_id"), table_name="question_response_items")
    op.drop_table("question_response_items")
    op.drop_index(op.f("ix_question_responses_resolution_id"), table_name="question_responses")
    op.drop_index(op.f("ix_question_responses_question_id"), table_name="question_responses")
    op.drop_table("question_responses")
    op.drop_index(op.f("ix_exam_resolutions_user_id"), table_name="exam_resolutions")
    op.drop_index(op.f("ix_exam_resolutions_exam_id"), table_name="exam_resolutions")
    op.drop_table("exam_resolutions")
    op.drop_column("questions", "expected_answer")
    op.drop_column("questions", "explanation")
