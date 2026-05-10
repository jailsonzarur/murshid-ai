import pytest
from httpx import AsyncClient

from src.shared.utils.auth import create_refresh_token


def describe_POST_auth_logout():
    @pytest.mark.asyncio
    async def it_should_logout_successfully(client: AsyncClient, test_user: dict):
        refresh_token = create_refresh_token(test_user["id"], "GUEST")

        response = await client.post("/auth/logout", json={"refresh_token": refresh_token})

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def it_should_logout_with_unknown_token(client: AsyncClient):
        response = await client.post("/auth/logout", json={"refresh_token": "unknown-token"})

        assert response.status_code == 200
