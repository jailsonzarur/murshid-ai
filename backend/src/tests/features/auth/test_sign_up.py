import pytest
from httpx import AsyncClient


def describe_POST_sign_up():
    @pytest.mark.asyncio
    async def it_should_sign_up_with_valid_data(client: AsyncClient):
        response = await client.post(
            "/auth/sign-up",
            json={"name": "New User", "email": "newuser@example.com", "password": "Password123"},
        )

        assert response.status_code == 201
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def it_should_not_sign_up_with_duplicate_email(client: AsyncClient, test_user: dict):
        response = await client.post(
            "/auth/sign-up",
            json={"name": "Another User", "email": test_user["email"], "password": "Password123"},
        )

        assert response.status_code == 409
        assert "Email ja cadastrado" in response.json()["errors"]

    @pytest.mark.asyncio
    async def it_should_reject_invalid_email(client: AsyncClient):
        response = await client.post(
            "/auth/sign-up",
            json={"name": "Test User", "email": "invalid-email", "password": "Password123"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def it_should_normalize_email_to_lowercase(client: AsyncClient):
        response = await client.post(
            "/auth/sign-up",
            json={"name": "Test User", "email": "UPPERCASE@EXAMPLE.COM", "password": "Password123"},
        )

        assert response.status_code == 201
