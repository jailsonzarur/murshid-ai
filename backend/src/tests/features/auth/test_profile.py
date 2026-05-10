from datetime import UTC, datetime

import jwt
import pytest
from httpx import AsyncClient

from src.shared.utils.auth import SECRET_KEY, create_access_token


def describe_GET_profile():
    @pytest.mark.asyncio
    async def it_should_return_profile_when_authenticated(client: AsyncClient, test_user: dict, guest_headers: dict):
        response = await client.get("/auth/profile", headers=guest_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == test_user["name"]
        assert data["email"] == test_user["email"]

    @pytest.mark.asyncio
    async def it_should_return_401_when_not_authenticated(client: AsyncClient):
        response = await client.get("/auth/profile")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def it_should_return_404_for_nonexistent_user(client: AsyncClient):
        token = create_access_token({"sub": "00000000-0000-0000-0000-000000000001", "role": "GUEST"})

        response = await client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def it_should_return_401_with_expired_token(client: AsyncClient):
        token = jwt.encode(
            {"sub": "1", "role": "GUEST", "type": "access", "exp": datetime(2000, 1, 1, tzinfo=UTC)},
            SECRET_KEY,
            algorithm="HS256",
        )

        response = await client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
        assert "expirado" in response.json()["errors"][0]
