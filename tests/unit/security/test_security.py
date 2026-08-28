from app.core.config.auth import JwtSettings
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_token,
)
from app.core.security.password import hash_password, verify_password


def _settings(**overrides) -> JwtSettings:
    values = {
        "secret_key": "test-secret",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
    }
    values.update(overrides)
    return JwtSettings(**values)


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_roundtrip():
    settings = _settings()

    token = create_access_token(subject="42", settings=settings, session_id="abc123")

    assert decode_access_token(token, settings) == "42"


def test_jwt_carries_session_id():
    settings = _settings()

    token = create_access_token(subject="42", settings=settings, session_id="sess-xyz")

    payload = decode_token(token, settings)
    assert payload["sub"] == "42"
    assert payload["sid"] == "sess-xyz"


def test_refresh_token_roundtrip_and_expiry():
    settings = _settings(refresh_token_expire_minutes=60)

    token = create_refresh_token(subject="42", settings=settings, session_id="sess-xyz")

    payload = decode_token(token, settings)
    assert payload["sub"] == "42"
    assert payload["sid"] == "sess-xyz"


def test_jwt_invalid_token():
    settings = _settings()

    assert decode_access_token("not-a-token", settings) is None


def test_jwt_wrong_secret():
    settings = _settings()
    other_settings = _settings(secret_key="other-secret")

    token = create_access_token(subject="42", settings=settings, session_id="abc")

    assert decode_access_token(token, other_settings) is None
