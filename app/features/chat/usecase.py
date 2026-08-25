from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context.budget import ContextBudget
from app.application.context.manager import ContextManager
from app.core.exceptions.business import BusinessException
from app.core.exceptions.error_codes import ErrorCode
from app.domain.llm import ChatMessage
from app.domain.model_profile import DEFAULT_MODEL
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
    ):
        self.chat_service = chatService
        self.session = session
        self.conversation_repository = ConversationRepository(session)
        self.message_repository = MessageRepository(session)
        self.context_manager = context_manager
        self.model_resolver = model_resolver
        self.context_budget = context_budget

    async def get_conversation(self, id: int) -> Conversation | None:
        return await self.conversation_repository.get_by_id(conversation_id=id)

    async def get_conversation_with_messages(self, id: int) -> Conversation | None:
        return await self.conversation_repository.get_with_messages(conversation_id=id)

    async def chat(
        self,
        conversation_id: int | None,
        message: str,
        model: str | None = None,
    ):
        try:

            if conversation_id is None:
                conversation = await self.conversation_repository.create(
                    title=message[:50]
                )
                messages = []

            else:
                conversation = await self.conversation_repository.get_with_messages(
                    conversation_id=conversation_id
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

            # Default ke model yang dikonfigurasi kalau client tidak memilih.
            resolved_model = self.model_resolver.resolve(model or DEFAULT_MODEL)

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

            llm_response = await self.chat_service.ask(context_result.messages)

            await self.message_repository.create(
                conversation_id=conversation.id,
                role="user",
                content=message,
            )

            await self.message_repository.create(
                conversation_id=conversation.id,
                role="assistant",
                content=llm_response.content,
            )

            await self.session.commit()

            return ChatResponse(
                conversation_id=conversation.id,
                data=llm_response,
                context_result=context_result,
            )

        except Exception:
            await self.session.rollback()
            raise
