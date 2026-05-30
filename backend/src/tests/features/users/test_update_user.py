import pytest
from faker import Faker
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.auth.utils import hash_password
from src.features.users.models import UserModel
from src.shared.enums.enums import UserRole

fake = Faker("pt_BR")
UNKNOWN_USER_ID = "00000000-0000-0000-0000-000000000001"


def describe_PUT_user():
    @pytest.mark.asyncio
    async def it_should_return_401_without_token(client: AsyncClient):
        response = await client.put(f"/users/{UNKNOWN_USER_ID}", json={"name": "Updated"})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def it_should_update_user_for_guest_user(client: AsyncClient, guest_headers: dict, test_user: dict):
        response = await client.put(f"/users/{test_user['id']}", json={"name": "Updated"}, headers=guest_headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def it_should_update_user(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
        user = UserModel(
            name="Original Name",
            email=fake.unique.email().lower(),
            password=hash_password("Password123"),
            role=UserRole.GUEST,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        response = await client.put(
            f"/users/{user.id}",
            json={"name": "Updated Name", "email": fake.unique.email(), "role": "ADMIN"},
            headers=auth_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def it_should_return_404_for_nonexistent_user(client: AsyncClient, auth_headers: dict):
        response = await client.put(f"/users/{UNKNOWN_USER_ID}", json={"name": "Updated"}, headers=auth_headers)

        assert response.status_code == 404
