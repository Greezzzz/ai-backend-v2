import os

# Set env SEBELUM app.main di-import (settings di-cache saat import).
# Rate limit tinggi supaya test tidak saling kena 429 (test berbagi IP testclient).
os.environ.setdefault("HTTP_RATE_LIMIT_REQUESTS_PER_MINUTE", "100000")

import pytest_asyncio  # noqa: E402

from app.core.database.config import DatabaseSettings  # noqa: E402
from app.core.database.engine import create_engine  # noqa: E402
from app.core.database.session import create_session_factory  # noqa: E402


@pytest_asyncio.fixture
async def session_factory():

    settings = DatabaseSettings()

    engine = create_engine(settings)

    factory = create_session_factory(engine)

    yield factory

    await engine.dispose()
