from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.chat.model import Conversation, Message


class ConversationRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        title: str,
        user_id: int,
    ) -> Conversation:

        conversation = Conversation(title=title, user_id=user_id)

        self.session.add(conversation)

        await self.session.flush()

        return conversation

    async def get_by_id(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:

        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_with_messages(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:

        result = await self.session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: int,
        limit: int = 50,
    ) -> list[tuple[Conversation, str | None]]:
        """Daftar percakapan milik user, urut terbaru dulu.

        Preview memakai pesan TERAKHIR per percakapan (scalar subquery pada
        messages, order created_at desc, limit 1). Percakapan tanpa pesan tetap
        muncul dengan preview NULL.
        """
        result = await self.session.execute(
            select(
                Conversation,
                select(Message.content)
                .where(Message.conversation_id == Conversation.id)
                .order_by(Message.created_at.desc())
                .limit(1)
                .correlate(Conversation)
                .scalar_subquery()
                .label("last_message"),
            )
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )

        return [
            (conversation, last_message_content)
            for conversation, last_message_content in result.all()
        ]


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