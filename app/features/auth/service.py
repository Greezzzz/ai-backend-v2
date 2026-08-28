from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.auth import JwtSettings
from app.core.exceptions.auth import (
    AuthenticationRequiredException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
)
from app.core.security.jwt import create_access_token, create_refresh_token, decode_token
from app.core.security.password import hash_password, verify_password
from app.core.security.session import generate_session_id
from app.core.security.session_store import SessionStore
from app.features.auth.model import User
from app.features.auth.repository import UserRepository
from app.features.auth.schemas import RegisterRequest, TokenResponse, UserResponse


class AuthService:

    def __init__(
        self,
        session: AsyncSession,
        jwt_settings: JwtSettings,
        session_store: SessionStore,
    ):
        self.session = session
        self.repository = UserRepository(session)
        self.jwt_settings = jwt_settings
        self.session_store = session_store

    async def register(self, request: RegisterRequest) -> UserResponse:
        if await self.repository.get_by_username(request.username) is not None:
            raise UserAlreadyExistsException(details={"field": "username"})

        if await self.repository.get_by_email(request.email) is not None:
            raise UserAlreadyExistsException(details={"field": "email"})

        user = await self.repository.create(
            username=request.username,
            email=request.email,
            password_hash=hash_password(request.password),
        )

        await self.session.commit()

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
        )

    async def login(self, username: str, password: str) -> TokenResponse:
        user = await self.repository.get_by_username(username)

        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsException()

        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, self.jwt_settings)

        if payload is None:
            raise AuthenticationRequiredException()

        user_id = payload.get("sub")

        if user_id is None:
            raise AuthenticationRequiredException()

        user = await self.repository.get_by_id(int(user_id))

        if user is None:
            raise AuthenticationRequiredException()

        # Refresh = rotasi session: session_id baru menimpa yang lama di Redis.
        return await self._issue_tokens(user)

    async def logout(self, user_id: int) -> None:
        await self.session_store.delete(user_id)

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self.repository.get_by_id(user_id)

    async def _issue_tokens(self, user: User) -> TokenResponse:
        session_id = generate_session_id()

        # Single session: SET session:{user.id} = session_id (menimpa login lama).
        await self.session_store.create(
            user_id=user.id,
            session_id=session_id,
            ttl_seconds=self.jwt_settings.refresh_token_expire_minutes * 60,
        )

        access_token = create_access_token(
            subject=str(user.id),
            settings=self.jwt_settings,
            session_id=session_id,
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            settings=self.jwt_settings,
            session_id=session_id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
