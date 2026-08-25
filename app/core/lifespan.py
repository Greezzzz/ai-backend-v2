from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.core.config.openai import HttpSettings, LimitSettings
from app.core.config.settings import get_settings
from app.core.database.config import DatabaseSettings
from app.core.database.engine import create_engine
from app.core.database.session import create_session_factory
from app.core.logging.config import setup_logging
from app.core.resources import Resources


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    timeout = get_timeout_settings(settings.openai.http)
    limit = get_limit_settings(settings.openai.limit)

    http = httpx.AsyncClient(
        timeout = timeout,
        limits = limit
    )

    app.state.resources = Resources(
        settings=settings,
        http_client=http
    )

    engine = create_engine(DatabaseSettings())
    session_factory = create_session_factory(engine)

    app.state.db_engine = engine
    app.state.db_session_factory = session_factory

    setup_logging()

    yield

    await http.aclose()
    await engine.dispose()


def get_timeout_settings(settings: HttpSettings):
    return httpx.Timeout(
        connect=settings.connect,
        read=settings.read,
        write=settings.write,
        pool=settings.pool
    )

def get_limit_settings(settings: LimitSettings):
    return httpx.Limits(
        keepalive_expiry=settings.keep_alive_expiry,
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections
    )