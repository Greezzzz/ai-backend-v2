import httpx

from app.core.config.retry import RetrySettings
from app.core.retry.policy import RetryPolicy


class OpenAIRetryPolicy(RetryPolicy):

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

        return min(
            delay,
            self._settings.max_delay
        )