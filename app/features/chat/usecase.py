import json
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context.budget import ContextBudget
from app.application.context.manager import ContextManager
from app.application.context.result import ContextResult
from app.core.exceptions.business import BusinessException
from app.core.exceptions.error_codes import ErrorCode
from app.core.metrics.chat import chat_messages_sent_total
from app.core.metrics.llm import llm_input_tokens_total, llm_output_tokens_total
from app.domain.llm import ChatMessage
from app.domain.model_resolver import ModelResolver
from app.features.chat.model import Conversation
from app.features.chat.repository import ConversationRepository, MessageRepository
from app.features.chat.schemas import ChatResponse
from app.features.chat.service import ChatService


class ChatUseCase:
    def __init__(
        self,
        chatService: ChatService,
        session: AsyncSession,
        context_manager: ContextManager,
        model_resolver: ModelResolver,
        context_budget: ContextBudget,
        default_model: str,
    ):
        self.chat_service = chatService
        self.session = session
        self.conversation_repository = ConversationRepository(session)
        self.message_repository = MessageRepository(session)
        self.context_manager = context_manager
        self.model_resolver = model_resolver
        self.context_budget = context_budget
        self.default_model = default_model

    async def get_conversation(self, id: int, user_id: int) -> Conversation | None:
        return await self.conversation_repository.get_by_id(
            conversation_id=id,
            user_id=user_id,
        )

    async def get_conversation_with_messages(
        self, id: int, user_id: int
    ) -> Conversation | None:
        return await self.conversation_repository.get_with_messages(
            conversation_id=id,
            user_id=user_id,
        )

    async def list_conversations(self, user_id: int):
        return await self.conversation_repository.list_by_user(user_id=user_id)

    async def _prepare_chat(
        self,
        conversation_id: int | None,
        message: str,
        user_id: int,
    ) -> tuple[Conversation, list[ChatMessage], ContextResult]:
        """Siapkan conversation + messages + context (dipakai chat & stream)."""
        if conversation_id is None:
            conversation = await self.conversation_repository.create(
                title=message[:50],
                user_id=user_id,
            )
            messages: list[ChatMessage] = []

        else:
            conversation = await self.conversation_repository.get_with_messages(
                conversation_id=conversation_id,
                user_id=user_id,
            )

            if conversation is None:
                raise BusinessException(
                    message=f"Conversation with id {conversation_id} not found.",
                    code=ErrorCode.CONVERSATION_NOT_FOUND,
                    status_code=404,
                )

            messages = [
                ChatMessage(role=item.role, content=item.content)
                for item in conversation.messages
            ]

        messages.append(ChatMessage(role="user", content=message))

        # Model selalu dari settings (.env: CHAT_MODEL) — resolve token
        # counter yang sesuai, supaya budget context konsisten dengan model
        # yang benar-benar dipakai request LLM.
        resolved_model = self.model_resolver.resolve(self.default_model)

        budget = ContextBudget(
            context_window=resolved_model.profile.context_window,
            reserved_output=(
                resolved_model.profile.max_output_tokens
                or self.context_budget.reserved_output
            ),
            safety_margin_ratio=self.context_budget.safety_margin_ratio,
        )

        context_manager = ContextManager(
            token_counter=resolved_model.token_counter,
            budget=budget,
        )

        context_result = context_manager.build_context(messages)

        return conversation, messages, context_result

    async def _save_messages(
        self,
        conversation: Conversation,
        user_message: str,
        assistant_content: str,
    ) -> None:
        await self.message_repository.create(
            conversation_id=conversation.id,
            role="user",
            content=user_message,
        )
        chat_messages_sent_total.labels(role="user").inc()

        await self.message_repository.create(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
        )
        chat_messages_sent_total.labels(role="assistant").inc()

        await self.session.commit()

    async def chat(
        self,
        conversation_id: int | None,
        message: str,
        user_id: int,
    ):
        try:
            conversation, messages, context_result = await self._prepare_chat(
                conversation_id=conversation_id,
                message=message,
                user_id=user_id,
            )
            llm_response = await self.chat_service.ask(context_result.messages)

            await self._save_messages(
                conversation=conversation,
                user_message=message,
                assistant_content=llm_response.content,
            )

            return ChatResponse(
                conversation_id=conversation.id,
                data=llm_response,
                context_result=context_result,
            )

        except Exception:
            await self.session.rollback()
            raise

    async def stream_chat(
        self,
        conversation_id: int | None,
        message: str,
        user_id: int,
    ) -> AsyncIterator[str]:
        """Streaming: yield event SSE. Pesan assistant disimpan setelah stream selesai.

        Format event:
        - data: {"delta": "..."}   → potongan teks
        - data: {"error": "..."}   → error di tengah stream
        - data: [DONE]             → selesai
        """
        conversation, messages, _ = await self._prepare_chat(
            conversation_id=conversation_id,
            message=message,
            user_id=user_id,
        )

        chunks: list[str] = []

        try:
            async for delta in self.chat_service.stream_ask(messages):
                chunks.append(delta)
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"

        except Exception as e:
            await self.session.rollback()
            error_msg = str(e) or type(e).__name__
            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
            return

        # Stream selesai → simpan user + assistant (teks penuh hasil akumulasi).
        try:
            await self._save_messages(
                conversation=conversation,
                user_message=message,
                assistant_content="".join(chunks),
            )
        except Exception:
            await self.session.rollback()
            yield f"data: {json.dumps({'error': 'failed to save messages'}, ensure_ascii=False)}\n\n"
            return

        # Token usage: chunk usage bisa muncul di posisi mana pun — client
        # menyimpannya selama stream. Tulis ke Prometheus + kirim ke klien
        # sebelum [DONE] (kalau ada; stream yang terputus mungkin tidak punya).
        usage = self.chat_service.client.last_usage

        if usage is not None:
            llm_input_tokens_total.labels(
                model=self.default_model, provider="openai"
            ).inc(usage.input_tokens)
            llm_output_tokens_total.labels(
                model=self.default_model, provider="openai"
            ).inc(usage.output_tokens)

            yield f"data: {json.dumps({'usage': usage.model_dump()}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"
