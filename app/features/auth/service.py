from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.auth import JwtSettings
from app.core.exceptions.auth import (
    InvalidCredentialsException,
    UserAlreadyExistsException,
)
from app.core.security.jwt import create_access_token
from app.core.security.password import hash_password, verify_password
from app.features.auth.model import User
from app.features.auth.repository import UserRepository
from app.features.auth.schemas import RegisterRequest, TokenResponse, UserResponse


class AuthService:

    def __init__(
        self,
        session: AsyncSession,
        jwt_settings: JwtSettings,
    ):
        self.session = session
        self.repository = UserRepository(session)
        self.jwt_settings = jwt_settings

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

        token = create_access_token(
            subject=str(user.id),
            settings=self.jwt_settings,
        )

        return TokenResponse(access_token=token)

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self.repository.get_by_id(user_id)
