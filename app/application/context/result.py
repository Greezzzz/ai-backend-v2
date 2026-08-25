from dataclasses import dataclass

from app.domain.llm import ChatMessage


@dataclass(frozen=True)
class ContextResult:
    messages: list[ChatMessage]
    estimated_tokens: int
