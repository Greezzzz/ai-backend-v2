from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBudget:
    context_window: int = 0
    reserved_output: int = 0
    safety_margin_ratio: float = 0.05

    @property
    def safety_margin_tokens(self) -> int:
        return int(self.context_window * self.safety_margin_ratio)

    @property
    def available_input_tokens(self) -> int:
        return self.context_window - self.reserved_output - self.safety_margin_tokens
