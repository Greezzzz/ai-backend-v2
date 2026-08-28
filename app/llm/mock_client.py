from collections.abc import AsyncIterator

from app.domain.llm import LLMRequest, LLMResponse, TokenUsage


class MockClient:

    def __init__(self):
        self.last_usage: TokenUsage | None = None

    async def chat(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=f"Mock {request.messages[-1].content}",
            model="mock-model",
            finish_reason="stop",
        )

    async def stream_chat(self, request: LLMRequest) -> AsyncIterator[str]:
        # Simulasikan streaming: pecah jawaban jadi kata per kata.
        words = f"Mock {request.messages[-1].content}".split()

        for word in words:
            yield word + " "
