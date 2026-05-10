from decouple import config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import IS_PRODUCTION

DATABASE_URL: str = str(config("DATABASE_URL", default="sqlite+aiosqlite:///./api_v2.db"))

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    DATABASE_URL,
    echo=not IS_PRODUCTION,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def import_models() -> None:
    from src.features.categories.models import CategoryModel  # noqa: F401
    from src.features.exams.models import ExamDocumentModel, ExamModel  # noqa: F401
    from src.features.questions.models import OptionModel, QuestionModel  # noqa: F401
    from src.features.users.models import UserModel  # noqa: F401


async def init_db() -> None:
    import_models()
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
