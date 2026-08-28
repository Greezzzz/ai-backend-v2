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


def _unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _register_and_login(client, prefix: str) -> dict:
    username = _unique_username(prefix)
    password = "supersecret123"

    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
    )
    login = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_conversation(client, headers: dict) -> int:
    response = client.post(
        "/api/chat/conversations",
        json={"message": "halo dari user A"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["conversation_id"]


def test_list_requires_jwt(client):
    response = client.get("/api/chat/conversations")
    assert response.status_code == 401


def test_get_conversation_requires_jwt(client):
    response = client.get("/api/chat/conversations/1")
    assert response.status_code == 401


def test_conversation_is_owned_by_creator(client):
    headers_a = _register_and_login(client, "owner")
    conversation_id = _create_conversation(client, headers_a)

    # User A melihat percakapannya di list.
    list_response = client.get(
        "/api/chat/conversations", headers=headers_a
    )
    assert list_response.status_code == 200
    ids = [c["id"] for c in list_response.json()["conversations"]]
    assert conversation_id in ids

    # User B tidak melihat percakapan A.
    headers_b = _register_and_login(client, "other")
    list_b = client.get("/api/chat/conversations", headers=headers_b)
    assert list_b.status_code == 200
    ids_b = [c["id"] for c in list_b.json()["conversations"]]
    assert conversation_id not in ids_b

    # User B tidak bisa GET percakapan milik A → 404.
    get_b = client.get(
        f"/api/chat/conversations/{conversation_id}", headers=headers_b
    )
    assert get_b.status_code == 404


def test_list_returns_preview_of_last_message(client):
    headers = _register_and_login(client, "preview")

    # Percakapan pertama (tidak ada pesan lanjutan).
    response = client.post(
        "/api/chat/conversations",
        json={"message": "pesan pertama"},
        headers=headers,
    )
    conversation_id = response.json()["conversation_id"]

    # Kirim lagi ke percakapan yang sama → preview = pesan terakhir.
    client.post(
        "/api/chat/conversations",
        json={"conversation_id": conversation_id, "message": "pesan kedua"},
        headers=headers,
    )

    list_response = client.get("/api/chat/conversations", headers=headers)
    conversations = list_response.json()["conversations"]

    match = next(c for c in conversations if c["id"] == conversation_id)
    # Preview = pesan TERAKHIR (respons assistant dari MockClient: "Mock <input>").
    assert match["last_message"] == "Mock pesan kedua"


def test_get_conversation_returns_message_history(client):
    headers = _register_and_login(client, "history")

    conv = client.post(
        "/api/chat/conversations",
        json={"message": "pesan pertama"},
        headers=headers,
    ).json()
    conversation_id = conv["conversation_id"]

    client.post(
        "/api/chat/conversations",
        json={"conversation_id": conversation_id, "message": "pesan kedua"},
        headers=headers,
    )

    detail = client.get(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    )
    assert detail.status_code == 200, detail.text

    body = detail.json()
    assert body["id"] == conversation_id
    assert body["title"] == "pesan pertama"

    messages = body["messages"]
    roles_contents = [(m["role"], m["content"]) for m in messages]
    assert roles_contents == [
        ("user", "pesan pertama"),
        ("assistant", "Mock pesan pertama"),
        ("user", "pesan kedua"),
        ("assistant", "Mock pesan kedua"),
    ]


def test_stream_persists_conversation_for_user(client):
    headers = _register_and_login(client, "stream")

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "pesan via stream"},
        headers=headers,
    ) as response:
        body = "".join(response.iter_text())

    assert "data: [DONE]" in body

    list_response = client.get("/api/chat/conversations", headers=headers)
    assert list_response.status_code == 200
    conversations = list_response.json()["conversations"]
    assert len(conversations) >= 1
