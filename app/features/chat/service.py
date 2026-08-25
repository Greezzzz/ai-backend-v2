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
