import threading
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.features.job import dependencies as job_deps
from app.features.job.tasks import echo_job
from app.main import app


def _fake_enqueue(type_: str, job_id: int, payload: dict) -> None:
    """Mock worker: jalankan task di thread terpisah.

    echo_job memakai asyncio.run() + engine DB sendiri, jadi butuh event
    loop milik thread ini (bukan loop TestClient).
    """
    threading.Thread(target=echo_job, args=(job_id, payload), daemon=True).start()


@pytest.fixture
def client():
    app.dependency_overrides[job_deps.get_enqueue_job] = lambda: _fake_enqueue

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _auth_headers(client) -> dict:
    username = f"job_{uuid.uuid4().hex[:8]}"
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


def _wait_succeeded(client, job_id: int, headers: dict, timeout: float = 5.0) -> dict:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        response = client.get(f"/api/jobs/{job_id}", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        if body["status"] == "succeeded":
            return body
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} not succeeded within {timeout}s")


def test_create_job_requires_jwt(client):
    response = client.post("/api/jobs", json={"type": "echo", "payload": {}})
    assert response.status_code == 401


def test_create_job_unknown_type(client):
    headers = _auth_headers(client)
    response = client.post(
        "/api/jobs",
        json={"type": "nope", "payload": {}},
        headers=headers,
    )
    assert response.status_code == 400


def test_create_and_get_job_lifecycle(client):
    headers = _auth_headers(client)

    # create → 201, status awal queued
    create = client.post(
        "/api/jobs",
        json={"type": "echo", "payload": {"text": "halo"}},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    created = create.json()
    assert created["status"] == "queued"
    # field None (result/error) di-exclude dari response (response_model_exclude_none)
    assert "result" not in created

    # mock worker menjalankan echo → polling sampai succeeded
    done = _wait_succeeded(client, created["id"], headers)
    assert done["status"] == "succeeded"
    assert done["result"] == "echo: halo"


def test_get_job_not_found(client):
    headers = _auth_headers(client)
    response = client.get("/api/jobs/999999", headers=headers)
    assert response.status_code == 404
    assert response.json()["code"] == "JOB_NOT_FOUND"