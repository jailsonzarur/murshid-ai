"""set null on lecture subject delete

Deleting a subject raised a ForeignKeyViolationError because lectures still
pointed at it. A lecture outlives its subject — losing the link is the right
outcome, and the delete dialog already says so.

subject_documents keeps CASCADE: its subject_id is NOT NULL, so SET NULL is not
even possible there, and a document without its subject means nothing.

Revision ID: 50f62533c526
Revises: c4c742d49ccf
Create Date: 2026-09-07
"""

from alembic import op

revision = '50f62533c526'
down_revision = 'c4c742d49ccf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('lectures_subject_id_fkey', 'lectures', type_='foreignkey')
    op.create_foreign_key(
        'lectures_subject_id_fkey',
        'lectures',
        'subjects',
        ['subject_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('lectures_subject_id_fkey', 'lectures', type_='foreignkey')
    op.create_foreign_key(
        'lectures_subject_id_fkey', 'lectures', 'subjects', ['subject_id'], ['id']
    )
