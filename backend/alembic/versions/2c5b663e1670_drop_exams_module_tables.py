"""drop exams module tables

Remove as tabelas do modulo de provas (exams, questions, resolutions), removido do projeto.
Operacao destrutiva: os dados nao sao recuperaveis por downgrade.
O schema original esta preservado na tag exams-v1.

Revision ID: 2c5b663e1670
Revises: a49eb2fdd835
Create Date: 2026-09-06 16:59:15.636638
"""

from alembic import op

revision = '2c5b663e1670'
down_revision = 'a49eb2fdd835'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f('ix_question_response_evaluations_response_id'), table_name='question_response_evaluations')
    op.drop_table('question_response_evaluations')

    op.drop_index(op.f('ix_question_response_items_response_id'), table_name='question_response_items')
    op.drop_table('question_response_items')

    op.drop_index(op.f('ix_question_responses_question_id'), table_name='question_responses')
    op.drop_index(op.f('ix_question_responses_resolution_id'), table_name='question_responses')
    op.drop_table('question_responses')

    op.drop_index(op.f('ix_exam_resolutions_exam_id'), table_name='exam_resolutions')
    op.drop_index(op.f('ix_exam_resolutions_user_id'), table_name='exam_resolutions')
    op.drop_table('exam_resolutions')

    op.drop_table('options')
    op.drop_table('questions')
    op.drop_table('exam_documents')
    op.drop_table('exams')


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade nao suportado: o modulo de provas foi removido e os dados dropados "
        "por esta migration nao sao recuperaveis. Para recuperar o schema, use a tag exams-v1."
    )
