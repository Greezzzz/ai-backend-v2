import asyncio
import time

from app.core.config.rate_limit import RateLimiterSettings
from app.core.rate_limiter.token_bucket import TokenBucketRateLimiter


async def test_consume():

    limiter = TokenBucketRateLimiter(
        settings=RateLimiterSettings(
            capacity=2,
            refill_per_second=1,
            acquire_timeout=2
        )
    )

    start = time.monotonic()

    await limiter.acquire()
    await limiter.acquire()

    elapsed = time.monotonic() - start

    print(f"consume elapsed: {elapsed:.3f}")


async def test_wait():

    limiter = TokenBucketRateLimiter(
        settings=RateLimiterSettings(
            capacity=1,
            refill_per_second=1,
            acquire_timeout=2
        )
    )

    start = time.monotonic()

    await limiter.acquire()
    await limiter.acquire()

    elapsed = time.monotonic() - start

    print(f"wait elapsed: {elapsed:.3f}")


async def test_concurrent():

    limiter = TokenBucketRateLimiter(
        settings=RateLimiterSettings(
            capacity=2,
            refill_per_second=1,
            acquire_timeout=2
        )
    )

    async def request(name):

        start = time.monotonic()
        print(f"{name} waiting...")
        await limiter.acquire()

        elapsed = time.monotonic() - start

        print(
            f"{name} acquired after {elapsed:.3f}"
        )


    await asyncio.gather(
        request("A"),
        request("B"),
        request("C"),
    )


async def test_timeout():

    limiter = TokenBucketRateLimiter(
        settings=RateLimiterSettings(
            capacity=1,
            refill_per_second=0.1,
            acquire_timeout=1
        )
    )

    await limiter.acquire()

    try:
        await limiter.acquire()
    except Exception as e:
        print(type(e).__name__)

async def main():

    print("--------TEST CONSUME----------")
    await test_consume()
    print("--------TEST WAIT----------")
    await test_wait()
    print("--------TEST CONCURRENT----------")
    await test_concurrent()
    print("--------TEST TIMEOUT----------")
    await test_timeout()


if __name__ == "__main__":
    asyncio.run(main())