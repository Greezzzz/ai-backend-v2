import random

import httpx

from app.core.config.retry import RetrySettings
from app.core.retry.policy import RetryPolicy


class AnthropicRetryPolicy(RetryPolicy):

    RETRYABLE_EXCEPTIONS = (
        httpx.TimeoutException,
        httpx.NetworkError,
    )

    def __init__(
            self,
            settings: RetrySettings
        ):
        self._settings = settings

    @property
    def max_attempt(self):
        return self._settings.max_attempt

    def should_retry(
            self,
            exception: Exception,
            attempt: int
    ) -> bool:

        if attempt >= self.max_attempt:
            return False

        if isinstance(
            exception,
            self.RETRYABLE_EXCEPTIONS
        ):
            return True

        if isinstance(
            exception,
            httpx.HTTPStatusError
        ):
            return exception.response.status_code == 429

        return False

    def next_delay(
            self,
            attempt
        ) -> float:

        delay = (
            self._settings.base_delay * self._settings.multiplier ** (attempt - 1)
        )

        delay = min(
            delay,
            self._settings.max_delay
        )

        # Full jitter: acak antara 0..delay supaya request yang gagal bersamaan
        # tidak retry bareng-bareng (thundering herd) — penting saat kena
        # rate limit (429) / timeout provider.
        if self._settings.enable_jitter:
            delay = random.uniform(0, delay)

        return delay