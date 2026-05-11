import pytest
from faker import Faker
from httpx import AsyncClient

fake = Faker("pt_BR")


def describe_POST_users():
    @pytest.mark.asyncio
    async def it_should_return_401_without_token(client: AsyncClient):
        response = await client.post(
            "/users",
            json={"name": "Test User", "email": "test@example.com", "password": "Password123"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def it_should_create_user_for_guest_user(client: AsyncClient, guest_headers: dict):
        response = await client.post(
            "/users",
            json={"name": "Test User", "email": "test@example.com", "password": "Password123"},
            headers=guest_headers,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def it_should_create_user_successfully(client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/users",
            json={"name": fake.name(), "email": fake.unique.email(), "password": "Password123", "role": "GUEST"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def it_should_return_409_for_duplicate_email(client: AsyncClient, auth_headers: dict):
        email = fake.unique.email()
        payload = {"name": fake.name(), "email": email, "password": "Password123"}
        await client.post("/users", json=payload, headers=auth_headers)

        response = await client.post("/users", json=payload, headers=auth_headers)

        assert response.status_code == 409
