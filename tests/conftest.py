import pytest_asyncio

from app.core.database.config import DatabaseSettings
from app.core.database.engine import create_engine
from app.core.database.session import create_session_factory


@pytest_asyncio.fixture
async def session_factory():

    settings = DatabaseSettings()

    engine = create_engine(settings)

    factory = create_session_factory(engine)

    yield factory

    await engine.dispose()