"""rename categories to subjects and scope them per user

Categories were global: no owner, name unique across the whole table. That is
fine for a label but breaks as soon as documents hang off a subject, since one
user's material would be visible to everyone.

The orphan rows are deleted first. They were created by the exams pipeline,
one per question topic, and that feature is gone.

Revision ID: 3f1a90b7c204
Revises: 2c5b663e1670
Create Date: 2026-09-06
"""

import sqlalchemy as sa

from alembic import op

revision = '3f1a90b7c204'
down_revision = '2c5b663e1670'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM categories WHERE id NOT IN "
        "(SELECT DISTINCT category_id FROM lectures WHERE category_id IS NOT NULL)"
    )

    op.rename_table('categories', 'subjects')
    op.execute('ALTER INDEX categories_pkey RENAME TO subjects_pkey')
    op.execute('ALTER TABLE subjects RENAME CONSTRAINT categories_name_key TO subjects_name_key')

    op.alter_column('lectures', 'category_id', new_column_name='subject_id')
    op.execute('ALTER TABLE lectures RENAME CONSTRAINT lectures_category_id_fkey TO lectures_subject_id_fkey')

    op.add_column('subjects', sa.Column('user_id', sa.Uuid(as_uuid=True), nullable=True))
    op.execute(
        "UPDATE subjects SET user_id = ("
        "SELECT l.user_id FROM lectures l WHERE l.subject_id = subjects.id "
        "GROUP BY l.user_id ORDER BY count(*) DESC LIMIT 1)"
    )
    op.execute('DELETE FROM subjects WHERE user_id IS NULL')
    op.alter_column('subjects', 'user_id', nullable=False)

    op.create_foreign_key(op.f('subjects_user_id_fkey'), 'subjects', 'users', ['user_id'], ['id'])
    op.create_index(op.f('ix_subjects_user_id'), 'subjects', ['user_id'])

    op.drop_constraint('subjects_name_key', 'subjects', type_='unique')
    op.create_unique_constraint('uq_subjects_user_id_name', 'subjects', ['user_id', 'name'])


def downgrade() -> None:
    op.drop_constraint('uq_subjects_user_id_name', 'subjects', type_='unique')
    op.create_unique_constraint('subjects_name_key', 'subjects', ['name'])

    op.drop_index(op.f('ix_subjects_user_id'), table_name='subjects')
    op.drop_constraint(op.f('subjects_user_id_fkey'), 'subjects', type_='foreignkey')
    op.drop_column('subjects', 'user_id')

    op.execute('ALTER TABLE lectures RENAME CONSTRAINT lectures_subject_id_fkey TO lectures_category_id_fkey')
    op.alter_column('lectures', 'subject_id', new_column_name='category_id')

    op.execute('ALTER TABLE subjects RENAME CONSTRAINT subjects_name_key TO categories_name_key')
    op.execute('ALTER INDEX subjects_pkey RENAME TO categories_pkey')
    op.rename_table('subjects', 'categories')
