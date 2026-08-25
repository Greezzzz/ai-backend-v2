from typing import Protocol
from app.domain.llm import LLMRequest, LLMResponse

class LLMProtocol(Protocol):

    async def chat(self, request: LLMRequest)-> LLMResponse:
        ...