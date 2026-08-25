from typing import Protocol


class TokenizedProtocol(Protocol):

    def count_token(self, text: str) -> int: ...
