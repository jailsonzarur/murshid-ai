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


async def close_db() -> None:
    await engine.dispose()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Registro dos models no metadata.
#
# Precisa acontecer no import, não numa função que alguém chame: quando isso
# dependia de init_db(), a API chamava e o worker não, e o FK de users ficava
# pendurado até estourar no flush — silenciosamente, e só no worker.
#
# Fica no fim do arquivo porque os models importam Base daqui.
from src.features.lectures.models import LectureModel, LectureSegmentModel  # noqa: E402,F401
from src.features.subjects.models import SubjectDocumentModel, SubjectModel  # noqa: E402,F401
from src.features.users.models import UserModel  # noqa: E402,F401
