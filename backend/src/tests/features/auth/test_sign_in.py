import pytest
from httpx import AsyncClient


def describe_POST_sign_in():
    @pytest.mark.asyncio
    async def it_should_sign_in_with_valid_credentials(client: AsyncClient, test_user: dict):
        response = await client.post(
            "/auth/sign-in",
            json={"email": test_user["email"], "password": test_user["password"]},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def it_should_not_sign_in_with_wrong_password(client: AsyncClient, test_user: dict):
        response = await client.post(
            "/auth/sign-in",
            json={"email": test_user["email"], "password": "wrongpassword"},
        )

        assert response.status_code == 400
        assert "Email ou senha incorretos" in response.json()["errors"]

    @pytest.mark.asyncio
    async def it_should_sign_in_with_uppercase_email(client: AsyncClient, test_user: dict):
        response = await client.post(
            "/auth/sign-in",
            json={"email": test_user["email"].upper(), "password": test_user["password"]},
        )

        assert response.status_code == 200
