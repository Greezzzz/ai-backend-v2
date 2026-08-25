from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.core.config.dependencies import get_resources
from app.core.resources import Resources
from app.features.auth.service import AuthService


def get_auth_service(
    session: AsyncSession = Depends(get_db),
    resources: Resources = Depends(get_resources),
) -> AuthService:
    return AuthService(
        session=session,
        jwt_settings=resources.settings.jwt,
    )
