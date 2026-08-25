from collections.abc import AsyncIterator
from typing import Protocol

from app.domain.llm import LLMRequest, LLMResponse


class LLMProtocol(Protocol):

    async def chat(self, request: LLMRequest) -> LLMResponse: ...

    def stream_chat(self, request: LLMRequest) -> AsyncIterator[str]:
        """Yield potongan teks (delta) dari respons streaming."""
        ...
