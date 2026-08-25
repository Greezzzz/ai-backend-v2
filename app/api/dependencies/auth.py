from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.core.config.dependencies import get_resources
from app.core.exceptions.auth import (
    AuthenticationRequiredException,
    InvalidApiKeyException,
)
from app.core.resources import Resources
from app.core.security.jwt import decode_access_token
from app.features.auth.model import User
from app.features.auth.repository import UserRepository

# Ambil token dari header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    resources: Resources = Depends(get_resources),
    session: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_access_token(token, resources.settings.jwt)

    if user_id is None:
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
