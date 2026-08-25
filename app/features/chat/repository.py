from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.chat.model import Conversation
from app.features.chat.model import Message


class ConversationRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        title: str,
    ) -> Conversation:

        conversation = Conversation(title=title)

        self.session.add(conversation)

        await self.session.flush()

        return conversation

    async def get_by_id(
        self,
        conversation_id: int,
    ) -> Conversation | None:

        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )

        return result.scalar_one_or_none()

    async def get_with_messages(self, conversation_id: int) -> Conversation | None:

        result = await self.session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )

        return result.scalar_one_or_none()


class MessageRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        conversation_id: int,
        role: str,
        content: str,
    ) -> Message:

        message = Message(conversation_id=conversation_id, role=role, content=content)

        self.session.add(message)

        await self.session.flush()

        return message
