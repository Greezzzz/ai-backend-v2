from fastapi.params import Depends
from app.core.resources import Resources
from app.llm.openai_client import OpenAIClient
from app.core.config.dependencies import get_resources
from app.provider.openai.dependencies import get_retry_executor
from app.core.retry.executor import RetryExecutor
from app.core.rate_limiter.limiter import RateLimiter
from app.core.rate_limiter.dependencies import get_rate_limiter

async def get_openai_client(
        resources: Resources = Depends(get_resources),
        retry : RetryExecutor = Depends(get_retry_executor),
        rate_limiter : RateLimiter = Depends(get_rate_limiter)
):
    return OpenAIClient(
        http= resources.http_client,
        settings= resources.settings.openai,
        retry_executor= retry,
        rate_limiter=rate_limiter
    )