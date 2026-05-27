import os
from collections.abc import AsyncGenerator

from faker import Faker

fake = Faker("pt_BR")

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from src.database import Base, get_db  # noqa: E402
from src.features.users.models import UserModel  # noqa: E402
from src.main import app  # noqa: E402
from src.shared.enums.enums import UserRole  # noqa: E402
from src.features.auth.utils import create_access_token, hash_password  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_engine, db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    test_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    app.dependency_overrides[get_db] = override_get_db

    from src.features.auth import middleware as permission

    original_session_maker = permission.AsyncSessionLocal
    permission.AsyncSessionLocal = test_session_maker

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            yield async_client
    finally:
        permission.AsyncSessionLocal = original_session_maker
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> dict:
    user = UserModel(
        name=fake.name(),
        email=fake.unique.email().lower(),
        password=hash_password("Password123"),
        role=UserRole.GUEST,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value,
        "password": "Password123",
    }


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> dict:
    user = UserModel(
        name=fake.name(),
        email=fake.unique.email().lower(),
        password=hash_password("Admin123"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value,
        "password": "Admin123",
    }


@pytest.fixture
def guest_token(test_user: dict) -> str:
    return create_access_token({"sub": str(test_user["id"]), "role": "GUEST"})


@pytest.fixture
def admin_token(admin_user: dict) -> str:
    return create_access_token({"sub": str(admin_user["id"]), "role": "ADMIN"})


@pytest.fixture
def guest_headers(guest_token: str) -> dict:
    return {"Authorization": f"Bearer {guest_token}"}


@pytest.fixture
def auth_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}
