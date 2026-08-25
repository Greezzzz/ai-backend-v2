from app.domain.llm import LLMRequest, LLMResponse


class MockClient:

    async def chat(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=f"Mock {request.messages[-1].content}",
            model="mock-model",
            finish_reason="stop",
        )
