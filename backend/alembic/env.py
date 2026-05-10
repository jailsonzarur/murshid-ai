import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import DATABASE_URL, Base  # noqa: E402
from src.features.categories.models import CategoryModel  # noqa: F401, E402
from src.features.exams.models import ExamDocumentModel, ExamModel  # noqa: F401, E402
from src.features.questions.models import OptionModel, QuestionModel  # noqa: F401, E402
from src.features.users.models import UserModel  # noqa: F401, E402

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(DATABASE_URL)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
