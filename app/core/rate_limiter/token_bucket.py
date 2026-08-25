import asyncio
import time

from app.core.config.rate_limit import RateLimiterSettings
from app.core.exceptions.rate_limiter import RateLimiterTimeoutException
from app.core.logging.logger import logger


class TokenBucketRateLimiter:

    def __init__(
            self,
            settings: RateLimiterSettings
        ):
        self._capacity = settings.capacity
        self._tokens = float(settings.capacity)

        self._refill_rate = settings.refill_per_second
        self._acquire_timeout = settings.acquire_timeout

        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        start = time.monotonic()

        while True:
            async with self._lock:
                self._refill()

                if self._consume():
                    return

                wait_time = (
                    1 - self._tokens
                ) / self._refill_rate

            elapsed = time.monotonic() - start

            if elapsed + wait_time > self._acquire_timeout:
                raise RateLimiterTimeoutException

            logger.warning(
                "rate_limiter_wait",
                delay=wait_time
            )
            await asyncio.sleep(wait_time)

    def _refill(self):
        now = time.monotonic()

        elapsed = now - self._last_refill

        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._refill_rate
        )

        self._last_refill = now

    def _consume(self):
        if self._tokens >= 1:

            self._tokens -= 1
            return True
        
        return False

    async def _wait(self):
        
        if self._refill_rate <= 0:
            raise RuntimeError(
                "Refill rate must be greater than zero"
            )

        tokens_needed = 1 - self._tokens

        wait_time = tokens_needed / self._refill_rate
        await asyncio.sleep(wait_time)