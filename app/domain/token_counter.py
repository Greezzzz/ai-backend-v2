from app.domain.token import TokenCounterProtocol


class TokenCounterRegistry:
    def __init__(self, counters: dict[str, TokenCounterProtocol]):
        self._counters = counters

    def get(self, model: str) -> TokenCounterProtocol:
        counter = self._counters.get(model)

        if counter is None:
            raise ValueError(f"Token counter not found for model: {model}")

        return counter
