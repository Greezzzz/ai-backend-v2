from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies.auth import get_current_user
from app.features.auth.dependencies import get_auth_service
from app.features.auth.model import User
from app.features.auth.schemas import (
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.features.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.register(request)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
):
    return await service.login(
        username=form_data.username,
        password=form_data.password,
    )


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
    )
