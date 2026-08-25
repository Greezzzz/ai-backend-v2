from collections.abc import AsyncIterator

from app.domain.llm import LLMRequest, LLMResponse
from app.llm.protocol import LLMProtocol


class ChatService:

    def __init__(
        self,
        client: LLMProtocol,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ):
        self.client = client
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def ask(self, messages) -> LLMResponse:

        req: LLMRequest = LLMRequest(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        res: LLMResponse = await self.client.chat(req)
        return res

    async def stream_ask(self, messages) -> AsyncIterator[str]:
        """Streaming: yield delta teks dari client LLM."""
        req: LLMRequest = LLMRequest(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        async for delta in self.client.stream_chat(req):
            yield delta
