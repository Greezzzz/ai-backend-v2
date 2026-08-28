import uuid

import pytest
from fastapi.testclient import TestClient

from app.llm.factory import get_chat_client
from app.llm.mock_client import MockClient
from app.main import app


@pytest.fixture
def client():
    app.dependency_overrides[get_chat_client] = lambda: MockClient()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _auth_headers(client) -> dict:
    username = f"stream_{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "supersecret123",
        },
    )
    login = client.post(
        "/api/auth/login",
        data={"username": username, "password": "supersecret123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_stream_requires_jwt(client):
    response = client.post("/api/chat/stream", json={"message": "halo"})
    assert response.status_code == 401


def test_stream_returns_sse_chunks(client):
    headers = _auth_headers(client)

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "halo dunia"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        body = "".join(response.iter_text())

    assert "data: " in body
    assert "delta" in body
    assert "data: [DONE]" in body


def test_stream_persists_conversation(client):
    headers = _auth_headers(client)

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "pesan pertama"},
        headers=headers,
    ) as response:
        body = "".join(response.iter_text())

    assert "data: [DONE]" in body
