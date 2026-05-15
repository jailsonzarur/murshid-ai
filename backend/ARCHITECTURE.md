# Backend Architecture Rules

## Feature services own database access

Every database query, creation, update, delete, transaction commit, rollback, flush, or refresh must live in a service
module inside one of the feature packages under `src/features`.

Routes, background tasks, graph nodes, middlewares, agents, and shared modules must call feature services instead of
calling SQLAlchemy directly.

When the operation belongs to an entity, put it in that entity's feature service. Examples:

- User queries and mutations belong in `src/features/users/services/user_service.py`.
- Exam queries and mutations belong in `src/features/exams/services/exam_service.py`.
- Category queries and mutations belong in `src/features/categories/services/category_service.py`.
- Question and option queries and mutations belong in `src/features/questions/services/question_service.py`.

Do not add repository modules. Services are the only application layer allowed to query or mutate the database.
