from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_db(
    request: Request
):
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.db_session_factory
    )

    async with session_factory() as session:
        yield session