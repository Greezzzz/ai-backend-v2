from fastapi import Depends

from app.core.config.dependencies import get_resources
from app.core.resources import Resources
from app.core.retry.executor import RetryExecutor
from app.core.retry.policy import RetryPolicy
from app.provider.openai.retry_policy import OpenAIRetryPolicy


def get_openai_retry(
    resources: Resources = Depends(get_resources),
) -> RetryPolicy:
    return OpenAIRetryPolicy(
        resources.settings.chat.retry
    )


def get_retry_executor(
    policy: RetryPolicy = Depends(
        get_openai_retry
    )
) -> RetryExecutor:
    return RetryExecutor(policy)