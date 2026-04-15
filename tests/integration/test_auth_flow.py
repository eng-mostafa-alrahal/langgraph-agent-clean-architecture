"""Integration test: full register → login → me flow.

NOTE: These tests require a running PostgreSQL database.
For CI, swap to the SQLite-backed fixtures or use testcontainers.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires running PostgreSQL — enable in CI with docker-compose")
async def test_register_and_login(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": "test@example.com", "password": "securepassword123"},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "securepassword123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "test@example.com"
