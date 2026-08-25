import pytest

from app.features.chat.model import Conversation


@pytest.mark.asyncio
async def test_create_session_factory(session_factory):

    async with session_factory() as session:

        conversation = Conversation(
            title= "Test Conversation"
        )

        session.add(conversation)

        await session.commit()
        await session.refresh(conversation)

        assert conversation.id is not None
        assert conversation.title == "Test Conversation"