from app.application.context.budget import ContextBudget


def test_available_budget():
    budget = ContextBudget(
        context_window=16_000, reserved_output=2_000, safety_margin_ratio=0.05
    )

    assert budget.safety_margin_tokens == 800
    assert budget.available_input_tokens == 13_200
