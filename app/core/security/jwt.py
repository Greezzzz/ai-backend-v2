from datetime import UTC, datetime, timedelta

import jwt

from app.core.config.auth import JwtSettings


def create_access_token(
    subject: str,
    settings: JwtSettings,
) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": subject,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_access_token(
    token: str,
    settings: JwtSettings,
) -> str | None:
    """Return the token subject (user id) or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except jwt.PyJWTError:
        return None

    return payload.get("sub")
