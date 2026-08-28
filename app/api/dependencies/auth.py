from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.core.config.dependencies import get_redis, get_resources
from app.core.exceptions.auth import (
    AuthenticationRequiredException,
    InvalidApiKeyException,
)
from app.core.resources import Resources
from app.core.security.jwt import decode_token
from app.core.security.session_store import SessionStore
from app.features.auth.model import User
from app.features.auth.repository import UserRepository

# Ambil token dari header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    resources: Resources = Depends(get_resources),
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> User:
    payload = decode_token(token, resources.settings.jwt)

    if payload is None:
        raise AuthenticationRequiredException()

    user_id = payload.get("sub")
    session_id = payload.get("sid")

    if user_id is None or session_id is None:
        raise AuthenticationRequiredException()

    # Single session: token valid hanya kalau session_id-nya masih yang aktif
    # di Redis. Login baru / refresh / logout akan mengubah session aktif.
    if not await SessionStore(redis).validate(int(user_id), session_id):
        raise AuthenticationRequiredException()

    user = await UserRepository(session).get_by_id(int(user_id))

    if user is None:
        raise AuthenticationRequiredException()

    return user


async def require_api_key(
    request: Request,
    resources: Resources = Depends(get_resources),
) -> None:
    api_key = request.headers.get("X-API-Key")

    if api_key is None or api_key != resources.settings.api_key_settings.key:
        raise InvalidApiKeyException()
