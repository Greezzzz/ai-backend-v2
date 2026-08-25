from fastapi import Depends

from app.api.dependencies.database import get_db
from app.application.context.budget import ContextBudget
from app.application.context.manager import ContextManager
from app.domain.model_profile import DEFAULT_MODEL, ModelProfile, ModelRegistry
from app.domain.model_resolver import ModelResolver
from app.domain.token_counter import TokenCounterRegistry
from app.domain.token import TokenCounterProtocol
from app.features.chat.service import ChatService
from app.features.chat.usecase import ChatUseCase
from app.infrastructure.tokenizer.deepseek.v4.token_counter import (
    DeepSeekV4TokenCounter,
)
from app.llm.dependencies import get_openai_client
from app.llm.protocol import LLMProtocol


# Singleton: AutoTokenizer.from_pretrained berat, jangan dibuat tiap request.
_token_counter_cache: TokenCounterProtocol | None = None


def _get_default_token_counter() -> TokenCounterProtocol:
    global _token_counter_cache

    if _token_counter_cache is None:
        _token_counter_cache = DeepSeekV4TokenCounter()

    return _token_counter_cache


def get_token_counter() -> TokenCounterProtocol:
    return _get_default_token_counter()


def _default_budget() -> ContextBudget:
    return ContextBudget(
        context_window=16_000,
        reserved_output=2_000,
        safety_margin_ratio=0.05,
    )


def get_context_manager(
    token_counter: TokenCounterProtocol = Depends(get_token_counter),
) -> ContextManager:
    return ContextManager(token_counter=token_counter, budget=_default_budget())


def get_context_budget() -> ContextBudget:
    return _default_budget()


def get_model_registry() -> ModelRegistry:
    return ModelRegistry(
        profiles=[
            ModelProfile(
                provider="deepseek",
                model=DEFAULT_MODEL,
                context_window=128_000,
                max_output_tokens=4_096,
            ),
        ]
    )


def get_token_counter_registry() -> TokenCounterRegistry:
    return TokenCounterRegistry(
        counters={
            DEFAULT_MODEL: _get_default_token_counter(),
        }
    )


def get_model_resolver(
    model_registry: ModelRegistry = Depends(get_model_registry),
    token_counter_registry: TokenCounterRegistry = Depends(get_token_counter_registry),
) -> ModelResolver:
    return ModelResolver(
        model_registry=model_registry,
        token_counter_registry=token_counter_registry,
    )


async def get_chat_service(client: LLMProtocol = Depends(get_openai_client)):
    return ChatService(client)


async def get_chat_usecase(
    service: ChatService = Depends(get_chat_service),
    session=Depends(get_db),
    context_manager=Depends(get_context_manager),
    model_resolver=Depends(get_model_resolver),
    context_budget=Depends(get_context_budget),
) -> ChatUseCase:
    return ChatUseCase(
        chatService=service,
        session=session,
        context_manager=context_manager,
        model_resolver=model_resolver,
        context_budget=context_budget,
    )
