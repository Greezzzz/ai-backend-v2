import uuid

import pytest

from app.features.auth.repository import UserRepository
from app.features.chat.repository import ConversationRepository, MessageRepository


def _unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def _create_user(session, prefix: str = "conv"):
    user_repository = UserRepository(session)
    user = await user_repository.create(
        username=_unique_username(prefix),
        email=f"{_unique_username(prefix)}@example.com",
        password_hash="not-a-real-hash",
    )
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_create_conversation(session_factory):

    async with session_factory() as session:

        user = await _create_user(session)
        repository = ConversationRepository(session)

        conversation = await repository.create(
            "Test Conversation",
            user_id=user.id,
        )

        await session.commit()

        assert conversation.id is not None
        assert conversation.title == "Test Conversation"
        assert conversation.user_id == user.id


@pytest.mark.asyncio
async def test_find_conversation_by_id(session_factory):

    async with session_factory() as session:

        user = await _create_user(session)
        repository = ConversationRepository(session)

        conversation = await repository.create(
            "Test Conversation",
            user_id=user.id,
        )

        await session.commit()

        result = await repository.get_by_id(conversation.id, user.id)

        assert result is not None
        assert result.id == conversation.id
        assert result.title == "Test Conversation"
        assert result.user_id == user.id


@pytest.mark.asyncio
async def test_get_by_id_respects_ownership(session_factory):

    async with session_factory() as session:

        owner = await _create_user(session, "owner")
        other = await _create_user(session, "other")
        repository = ConversationRepository(session)

        conversation = await repository.create(
            "Owned Conversation",
            user_id=owner.id,
        )

        await session.commit()

        # Owner bisa ambil, user lain tidak.
        assert await repository.get_by_id(conversation.id, owner.id) is not None
        assert await repository.get_by_id(conversation.id, other.id) is None


@pytest.mark.asyncio
async def test_create_conversation_with_message(session_factory):

    async with session_factory() as session:

        user = await _create_user(session)
        conversation_repository = ConversationRepository(session)
        message_repository = MessageRepository(session)

        conversation = await conversation_repository.create(
            "Test Conversation",
            user_id=user.id,
        )

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

        user = await _create_user(session)
        conversation_repository = ConversationRepository(session)
        message_repository = MessageRepository(session)

        conversation = await conversation_repository.create(
            "Test Conversation",
            user_id=user.id,
        )

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

        result = await conversation_repository.get_with_messages(
            conversation.id,
            user.id,
        )

        assert result is not None
        assert result.id == conversation.id
        assert result.title == "Test Conversation"
        assert result.user_id == user.id
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "assistant"
