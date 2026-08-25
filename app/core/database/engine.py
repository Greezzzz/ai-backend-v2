from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database.config import DatabaseSettings


def create_engine(settings: DatabaseSettings):

    return create_async_engine(
        settings.url,
        pool_pre_ping=True
    )