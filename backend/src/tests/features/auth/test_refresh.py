import pytest
from httpx import AsyncClient

from src.shared.utils.auth import create_refresh_token


def describe_POST_auth_refresh():
    @pytest.mark.asyncio
    async def it_should_refresh_tokens(client: AsyncClient, test_user: dict):
        refresh_token = create_refresh_token(test_user["id"], "GUEST")

        response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["access_token"]
        assert data["refresh_token"]

    @pytest.mark.asyncio
    async def it_should_reject_invalid_refresh_token(client: AsyncClient):
        response = await client.post("/auth/refresh", json={"refresh_token": "invalid-token"})

        assert response.status_code == 401
