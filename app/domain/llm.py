from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str

class LLMRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: TokenUsage | None = None
    finish_reason: str | None = None