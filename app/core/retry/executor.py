import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.logging.logger import logger
from app.core.metrics.retry import retry_attempts_total, retry_exhausted_total
from app.core.retry.policy import RetryPolicy

T = TypeVar("T")

class RetryExecutor:

    def __init__(
            self,
            policy: RetryPolicy
    ):
        self._policy = policy

    async def execute(
            self,
            operation: Callable[[], Awaitable[T]],
            operation_name: str | None = None
    )-> T:
        attempt = 1

        while True:

            try:
                return await operation()

            except Exception as exc:

                if not self._policy.should_retry(
                    exc,
                    attempt
                ):
                    retry_exhausted_total.labels(
                        operation=operation_name or operation.__name__,
                        exception_type=type(exc).__name__
                    ).inc()
                    raise 

                delay = self._policy.next_delay(
                    attempt
                )

                logger.warning(
                    "retry_attempt",
                    attempt= attempt,
                    delay= delay
                )

                retry_attempts_total.labels(
                    attempt=attempt,
                    operation=operation_name or operation.__name__
                ).inc()


                await asyncio.sleep(delay)

                attempt += 1