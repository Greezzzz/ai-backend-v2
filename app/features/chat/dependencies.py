from fastapi import Depends

from app.api.dependencies.database import get_db
from app.application.context.budget import ContextBudget
from app.application.context.manager import ContextManager
from app.core.config.settings import Settings, get_settings
from app.domain.model_profile import ModelProfile, ModelRegistry
from app.domain.model_resolver import ModelResolver
from app.domain.token import TokenCounterProtocol
from app.domain.token_counter import TokenCounterRegistry
from app.features.chat.service import ChatService
from app.features.chat.usecase import ChatUseCase
from app.features.rag.dependencies import get_rag_service
from app.features.rag.service import RagService
from app.infrastructure.tokenizer.deepseek.v4.token_counter import (
    DeepSeekV4TokenCounter,
)
from app.infrastructure.tokenizer.openai.token_counter import OpenAITokenCounter
from app.llm.factory import get_chat_client
from app.llm.protocol import LLMProtocol

# Singleton: AutoTokenizer.from_pretrained (DeepSeek) berat, jangan dibuat tiap request.
_token_counter_cache: TokenCounterProtocol | None = None
_token_counter_key: tuple[str, str] | None = None


def _get_default_token_counter(
    model: str, token_correction: int, provider: str = "openai"
) -> TokenCounterProtocol:
    """Singleton token counter — dibuat sekali per (provider, model).

    Pilihan tokenizer:
    - provider `openai` + model DeepSeek → `DeepSeekV4TokenCounter`
      (encoding DSV4 + token correction khas DeepSeek).
    - provider `openai` + model lain → `OpenAITokenCounter` (tiktoken).
    - provider lain → belum tersedia.
    """
    if provider != "openai":
        raise NotImplementedError(
            f"tokenizer untuk provider '{provider}' belum tersedia"
        )

    global _token_counter_cache, _token_counter_key

    if _token_counter_cache is None or _token_counter_key != (provider, model):
        if "deepseek" in model.lower():
            _token_counter_cache = DeepSeekV4TokenCounter(
                model=f"deepseek-ai/{model}",
                token_correction=token_correction,
            )
        else:
            _token_counter_cache = OpenAITokenCounter(
                model=model,
                token_correction=token_correction,
            )
        _token_counter_key = (provider, model)

    return _token_counter_cache


def get_token_counter(
    settings: Settings = Depends(get_settings),
) -> TokenCounterProtocol:
    return _get_default_token_counter(
        model=settings.chat_model,
        token_correction=settings.chat_token_correction,
        provider=settings.chat_provider,
    )


def _default_budget() -> ContextBudget:
    # Fallback: nilai dipakai kalau ModelProfile tidak menyediakan
    # (context_window selalu dari ModelProfile di usecase).
    return ContextBudget(
        reserved_output=2_000,
        safety_margin_ratio=0.05,
    )


def get_context_manager(
    token_counter: TokenCounterProtocol = Depends(get_token_counter),
) -> ContextManager:
    return ContextManager(token_counter=token_counter, budget=_default_budget())


def get_context_budget() -> ContextBudget:
    return _default_budget()


def get_model_registry(
    settings: Settings = Depends(get_settings),
) -> ModelRegistry:
    """Registry model — dibangun dari settings (.env: CHAT_MODEL, dll)."""
    return ModelRegistry(
        profiles=[
            ModelProfile(
                provider=settings.chat_provider,
                model=settings.chat_model,
                context_window=settings.chat_context_window,
                max_output_tokens=settings.chat_max_output_tokens,
            ),
        ]
    )


def get_token_counter_registry(
    settings: Settings = Depends(get_settings),
) -> TokenCounterRegistry:
    return TokenCounterRegistry(
        counters={
            settings.chat_model: _get_default_token_counter(
                model=settings.chat_model,
                token_correction=settings.chat_token_correction,
                provider=settings.chat_provider,
            ),
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


async def get_chat_service(
    client: LLMProtocol = Depends(get_chat_client),
    settings: Settings = Depends(get_settings),
):
    return ChatService(
        client,
    )


async def get_chat_usecase(
    service: ChatService = Depends(get_chat_service),
    session=Depends(get_db),
    context_manager=Depends(get_context_manager),
    model_resolver=Depends(get_model_resolver),
    context_budget=Depends(get_context_budget),
    settings: Settings = Depends(get_settings),
    rag_service: RagService = Depends(get_rag_service),
) -> ChatUseCase:
    return ChatUseCase(
        chatService=service,
        session=session,
        context_manager=context_manager,
        model_resolver=model_resolver,
        context_budget=context_budget,
        default_model=settings.chat_model,
        rag_service=rag_service,
    )
