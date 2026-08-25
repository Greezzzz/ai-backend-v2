import pytest

from app.features.chat.repository import ConversationRepository, MessageRepository


@pytest.mark.asyncio
async def test_create_conversation(session_factory):

    async with session_factory() as session:

        repository = ConversationRepository(session)

        conversation = await repository.create("Test Conversation")

        await session.commit()

        assert conversation.id is not None
        assert conversation.title == "Test Conversation"


@pytest.mark.asyncio
async def test_find_conversation_by_id(session_factory):

    async with session_factory() as session:

        repository = ConversationRepository(session)

        conversation = await repository.create("Test Conversation")

        await session.commit()

        result = await repository.get_by_id(conversation.id)

        assert result is not None
        assert result.id == conversation.id
        assert result.title == "Test Conversation"


@pytest.mark.asyncio
async def test_create_conversation_with_message(session_factory):

    async with session_factory() as session:

        conversation_repository = ConversationRepository(session)
        message_repository = MessageRepository(session)

        conversation = await conversation_repository.create("Test Conversation")

        message = await message_repository.create(
            conversation_id=conversation.id,
            role="user",
            content="Hello, this is a test message.",
        )

        await session.commit()

        assert conversation.id is not None
        assert conversation.title == "Test Conversation"
        assert message.id is not None
        assert message.conversation_id == conversation.id
        assert message.role == "user"
        assert message.content == "Hello, this is a test message."


@pytest.mark.asyncio
async def test_find_conversation_with_messages(session_factory):

    async with session_factory() as session:

        conversation_repository = ConversationRepository(session)
        message_repository = MessageRepository(session)

        conversation = await conversation_repository.create("Test Conversation")

        await message_repository.create(
            conversation_id=conversation.id,
            role="user",
            content="Hello, this is the first test message.",
        )

        await message_repository.create(
            conversation_id=conversation.id,
            role="assistant",
            content="Hello, this is the second test message.",
        )

        await session.commit()

        result = await conversation_repository.get_with_messages(conversation.id)

        assert result is not None
        assert result.id == conversation.id
        assert result.title == "Test Conversation"
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "assistant"
