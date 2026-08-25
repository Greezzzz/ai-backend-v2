from app.core.security.jwt import create_access_token, decode_access_token
from app.core.security.password import hash_password, verify_password
from app.core.config.auth import JwtSettings


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_roundtrip():
    settings = JwtSettings(
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
    )

    token = create_access_token(subject="42", settings=settings)

    assert decode_access_token(token, settings) == "42"


def test_jwt_invalid_token():
    settings = JwtSettings(
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
    )

    assert decode_access_token("not-a-token", settings) is None


def test_jwt_wrong_secret():
    settings = JwtSettings(
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
    )
    other_settings = JwtSettings(
        secret_key="other-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
    )

    token = create_access_token(subject="42", settings=settings)

    assert decode_access_token(token, other_settings) is None
