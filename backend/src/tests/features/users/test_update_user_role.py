import pytest
from faker import Faker
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.auth.utils import hash_password
from src.features.users.models import UserModel
from src.shared.enums.enums import UserRole

fake = Faker("pt_BR")
UNKNOWN_USER_ID = "00000000-0000-0000-0000-000000000001"


def describe_PATCH_user_role():
    @pytest.mark.asyncio
    async def it_should_return_401_without_token(client: AsyncClient):
        response = await client.patch(f"/users/{UNKNOWN_USER_ID}/role", json={"role": "ADMIN"})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def it_should_update_role_for_guest_user(client: AsyncClient, guest_headers: dict, test_user: dict):
        response = await client.patch(f"/users/{test_user['id']}/role", json={"role": "ADMIN"}, headers=guest_headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def it_should_update_role(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
        user = UserModel(
            name=fake.name(),
            email=fake.unique.email(),
            password=hash_password("Password123"),
            role=UserRole.GUEST,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        response = await client.patch(f"/users/{user.id}/role", json={"role": "ADMIN"}, headers=auth_headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def it_should_return_422_for_invalid_role(client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            f"/users/{UNKNOWN_USER_ID}/role",
            json={"role": "INVALID_ROLE"},
            headers=auth_headers,
        )

        assert response.status_code == 422
