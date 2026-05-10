import pytest
from faker import Faker
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.users.models import UserModel
from src.shared.enums.enums import UserRole
from src.shared.utils.auth import hash_password

fake = Faker("pt_BR")
UNKNOWN_USER_ID = "00000000-0000-0000-0000-000000000001"


def describe_DELETE_user():
    @pytest.mark.asyncio
    async def it_should_return_401_without_token(client: AsyncClient):
        response = await client.delete(f"/users/{UNKNOWN_USER_ID}")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def it_should_return_404_for_guest_user_when_user_does_not_exist(client: AsyncClient, guest_headers: dict):
        response = await client.delete(f"/users/{UNKNOWN_USER_ID}", headers=guest_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def it_should_delete_user_successfully(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
        user = UserModel(
            name=fake.name(),
            email=fake.unique.email(),
            password=hash_password("Password123"),
            role=UserRole.GUEST,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        response = await client.delete(f"/users/{user.id}", headers=auth_headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def it_should_return_400_when_deleting_self(client: AsyncClient, auth_headers: dict, admin_user: dict):
        response = await client.delete(f"/users/{admin_user['id']}", headers=auth_headers)

        assert response.status_code == 400
