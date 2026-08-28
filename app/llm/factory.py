from fastapi import Depends

from app.core.config.dependencies import get_resources
from app.core.rate_limiter.dependencies import get_rate_limiter
from app.core.rate_limiter.limiter import RateLimiter
from app.core.resources import Resources
from app.core.retry.executor import RetryExecutor
from app.llm.protocol import LLMProtocol
from app.provider.anthropic.retry_policy import AnthropicRetryPolicy
from app.provider.openai.retry_policy import OpenAIRetryPolicy


async def get_chat_client(
    resources: Resources = Depends(get_resources),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> LLMProtocol:
    """Pilih client chat berdasarkan `CHAT_PROVIDER`.

    Provider menentukan client (wire format), retry policy, dan metrics label.
    `CHAT_*` settings tetap satu blok (flat) yang dibaca provider aktif.
    """
    provider = resources.settings.chat_provider
    settings = resources.settings.chat

    if provider == "openai":
        from app.llm.openai_client import OpenAIClient

        retry_executor = RetryExecutor(OpenAIRetryPolicy(settings.retry))
        return OpenAIClient(
            http=resources.http_client,
            settings=settings,
            retry_executor=retry_executor,
            rate_limiter=rate_limiter,
        )

    if provider == "anthropic":
        from app.llm.anthropic_client import AnthropicClient

        retry_executor = RetryExecutor(AnthropicRetryPolicy(settings.retry))
        return AnthropicClient(
            http=resources.http_client,
            settings=settings,
            retry_executor=retry_executor,
            rate_limiter=rate_limiter,
        )

    raise ValueError(f"unsupported chat_provider: {provider}")