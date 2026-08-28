import pytest
from fastapi.testclient import TestClient

from app.core.exceptions.base import AppException
from app.main import app


@pytest.fixture
def client():
    # TestClient tanpa context manager: tidak menjalankan lifespan,
    # jadi tidak butuh .env / DB / HTTP client.
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_not_found(client):
    response = client.get("/")
    assert response.status_code == 404


def test_app_exception_handler(client):
    @app.get("/_test/app-error")
    async def _raise_app_error():
        raise AppException(
            message="boom",
            code="TEST_ERROR",
            status_code=422,
            details={"reason": "unit test"},
        )

    response = client.get("/_test/app-error")
    assert response.status_code == 422

    body = response.json()
    assert body["code"] == "TEST_ERROR"
    assert body["message"] == "boom"
    assert body["details"] == {"reason": "unit test"}


def test_trace_middleware_sets_trace_id(client):
    response = client.get("/health")
    assert response.status_code == 200

    trace_id = response.headers.get("X-Trace-Id")
    assert trace_id is not None
    assert len(trace_id) == 32  # uuid4().hex


def test_trace_middleware_respects_incoming_trace_id(client):
    response = client.get("/health", headers={"X-Trace-Id": "my-custom-trace"})
    assert response.status_code == 200

    # X-Client-Trace-Id selalu echo id klien.
    assert response.headers.get("X-Client-Trace-Id") == "my-custom-trace"

    # X-Trace-Id = id server: 32-hex OTel kalau span aktif, atau id klien kalau
    # fallback (OTel mati). Tergantung state provider global dari test lain.
    server_trace_id = response.headers.get("X-Trace-Id")
    assert server_trace_id in ("my-custom-trace",) or (
        len(server_trace_id) == 32
        and all(ch in "0123456789abcdef" for ch in server_trace_id)
    )
