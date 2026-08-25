from typing import Protocol

from app.domain.llm import ChatMessage


class TokenCounterProtocol(Protocol):
    def count_messages(self, message: list[ChatMessage]) -> int: ...
