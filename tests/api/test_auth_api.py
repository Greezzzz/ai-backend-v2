import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config.settings import get_settings
from app.main import app


@pytest.fixture
def client():
    # Lifespan dijalankan: butuh .env (settings + DB).
    with TestClient(app) as c:
        yield c


@pytest.fixture
def api_key():
    return get_settings().api_key_settings.key


def _unique_username(prefix: str) -> str:
    # Username unik per run: test memakai DB asli, jadi harus independen
    # terhadap user dari run sebelumnya.
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def test_health_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_requires_api_key(client):
    response = client.get("/metrics")
    assert response.status_code == 401

    response = client.get("/metrics", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_metrics_with_api_key(client, api_key):
    response = client.get("/metrics", headers={"X-API-Key": api_key})
    assert response.status_code == 200


def test_api_endpoint_requires_jwt(client):
    response = client.get("/api/chat/conversations/1")
    assert response.status_code == 401


def test_register_login_me_flow(client):
    username = _unique_username("flow")
    password = "supersecret123"

    # register
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["username"] == username

    # login (form)
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    assert token
    assert response.json()["refresh_token"]

    # me with token
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["username"] == username


def test_single_session_kicks_previous_login(client):
    username = _unique_username("single")
    password = "supersecret123"

    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
    )

    first = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    ).json()
    second = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    ).json()

    # Token pertama sudah tidak valid (session ditimpa login kedua).
    me_first = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )
    assert me_first.status_code == 401

    # Token kedua valid.
    me_second = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )
    assert me_second.status_code == 200


def test_refresh_rotates_session(client):
    username = _unique_username("refresh")
    password = "supersecret123"

    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
    )
    tokens = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    ).json()

    # Refresh → token baru.
    refreshed = client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    new_tokens = refreshed.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"]

    # Session dirotasi: access token lama 401, yang baru 200.
    me_old = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_old.status_code == 401

    me_new = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert me_new.status_code == 200


def test_refresh_with_invalid_token_rejected(client):
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "garbage-token"},
    )
    assert response.status_code == 401


def test_logout_invalidates_session(client):
    username = _unique_username("logout")
    password = "supersecret123"

    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
    )
    tokens = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    ).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Sebelum logout: valid.
    assert client.get("/api/auth/me", headers=headers).status_code == 200

    # Logout → session dihapus.
    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 204

    # Sesudah logout: 401 (access token tidak lagi valid).
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_login_wrong_password(client):
    # User tidak harus ada — login dengan password salah harus 401.
    username = _unique_username("nouser")
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_duplicate_register(client):
    username = _unique_username("dup")

    first = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "supersecret123",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "supersecret123",
        },
    )
    # kedua kalinya harus 409
    assert second.status_code == 409


def test_rate_limit_store_blocks_excess():
    # Unit test store langsung (bukan via HTTP, karena limit test tinggi).
    from app.core.rate_limiter.http_store import InMemoryRateLimitStore

    store = InMemoryRateLimitStore(limit=2, window_seconds=60)

    assert store.is_allowed("client-1") is True
    assert store.is_allowed("client-1") is True
    assert store.is_allowed("client-1") is False  # limit 2 tercapai

    # client lain tidak terpengaruh
    assert store.is_allowed("client-2") is True
