import asyncio

from app.core.context.trace import (
    create_trace_id,
    get_trace_id,
)


async def worker(name):

    print(
        name,
        get_trace_id()
    )


async def main():

    create_trace_id()

    print(
        "main",
        get_trace_id()
    )

    await asyncio.gather(
        worker("A"),
        worker("B"),
    )


if __name__ == "__main__":
    asyncio.run(main())