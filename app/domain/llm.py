from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class LLMRequest(BaseModel):
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    # Estimasi input token dari tokenizer lokal (context manager) — metadata
    # observability untuk dibandingkan dengan usage aktual provider di span.
    estimated_tokens: int | None = None


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: TokenUsage | None = None
    finish_reason: str | None = None
