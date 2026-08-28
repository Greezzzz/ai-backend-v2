from fastapi import Depends

from app.core.config.dependencies import get_resources
from app.core.resources import Resources
from app.core.retry.executor import RetryExecutor
from app.core.retry.policy import RetryPolicy
from app.provider.anthropic.retry_policy import AnthropicRetryPolicy


def get_anthropic_retry(
    resources: Resources = Depends(get_resources),
) -> RetryPolicy:
    return AnthropicRetryPolicy(
        resources.settings.chat.retry
    )


def get_retry_executor(
    policy: RetryPolicy = Depends(
        get_anthropic_retry
    )
) -> RetryExecutor:
    return RetryExecutor(policy)