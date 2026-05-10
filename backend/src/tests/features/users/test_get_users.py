import pytest
from httpx import AsyncClient


def describe_GET_users():
    @pytest.mark.asyncio
    async def it_should_return_401_without_token(client: AsyncClient):
        response = await client.get("/users/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def it_should_return_users_list_for_guest_user(client: AsyncClient, guest_headers: dict, test_user: dict):
        response = await client.get("/users/", headers=guest_headers)

        assert response.status_code == 200
        assert response.json()["data"][0]["id"] == str(test_user["id"])

    @pytest.mark.asyncio
    async def it_should_return_users_list(client: AsyncClient, auth_headers: dict, admin_user: dict):
        response = await client.get("/users/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        assert "password" not in data[0]
