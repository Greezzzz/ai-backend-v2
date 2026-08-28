from collections.abc import AsyncIterator

from app.domain.llm import LLMRequest, LLMResponse
from app.llm.protocol import LLMProtocol


class ChatService:

    def __init__(
        self,
        client: LLMProtocol,
    ):
        self.client = client

    async def ask(self, messages) -> LLMResponse:

        req: LLMRequest = LLMRequest(
            messages=messages,
        )

        res: LLMResponse = await self.client.chat(req)
        return res

    async def stream_ask(self, messages) -> AsyncIterator[str]:
        """Streaming: yield delta teks dari client LLM."""
        req: LLMRequest = LLMRequest(
            messages=messages,
        )

        async for delta in self.client.stream_chat(req):
            yield delta
