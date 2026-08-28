from datetime import UTC, datetime, timedelta

import jwt

from app.core.config.auth import JwtSettings


def create_access_token(
    subject: str,
    settings: JwtSettings,
    session_id: str,
) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": subject,
        "sid": session_id,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def create_refresh_token(
    subject: str,
    settings: JwtSettings,
    session_id: str,
) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.refresh_token_expire_minutes
    )

    payload = {
        "sub": subject,
        "sid": session_id,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_token(
    token: str,
    settings: JwtSettings,
) -> dict | None:
    """Return the full token payload or None if invalid/expired."""
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except jwt.PyJWTError:
        return None


def decode_access_token(
    token: str,
    settings: JwtSettings,
) -> str | None:
    """Return the token subject (user id) or None if invalid/expired."""
    payload = decode_token(token, settings)

    if payload is None:
        return None

    return payload.get("sub")
