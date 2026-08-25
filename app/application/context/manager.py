from app.application.context.budget import ContextBudget
from app.application.context.result import ContextResult
from app.domain.llm import ChatMessage
from app.domain.token import TokenCounterProtocol


class ContextManager:
    def __init__(self, token_counter: TokenCounterProtocol, budget: ContextBudget):
        self.token_counter = token_counter
        self.budget = budget

    def build_context(self, messages: list[ChatMessage]) -> ContextResult:

        if not messages:
            return ContextResult(messages=[], estimated_tokens=0)

        selected: list[ChatMessage] = []
        current_token = 0

        for message in reversed(messages):
            candidate = [message, *selected]

            token_count = self.token_counter.count_messages(candidate)

            if current_token + token_count > self.budget.available_input_tokens:
                break

            selected = candidate
            estimated_tokens = token_count

        return ContextResult(messages=selected, estimated_tokens=estimated_tokens)
