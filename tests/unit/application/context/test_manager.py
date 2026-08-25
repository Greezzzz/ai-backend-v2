from app.application.context.budget import ContextBudget
from app.application.context.manager import ContextManager
from app.domain.llm import ChatMessage

# class FakeTokenCounter:
#     def count_messages(self, messages):
#         return sum(len(message.content) for message in messages)


# def test_build_context_keeps_recent_messages():

#     token_counter = FakeTokenCounter()

#     budget = ContextBudget(
#         context_window=20,
#         reserved_output=0,
#         safety_margin_ratio=0,
#     )

#     manager = ContextManager(
#         token_counter=token_counter,
#         budget=budget,
#     )

#     messages = [
#         ChatMessage(role="user", content="12345"),
#         ChatMessage(role="assistant", content="12345"),
#         ChatMessage(role="user", content="12345"),
#         ChatMessage(role="assistant", content="12345"),
#         ChatMessage(role="user", content="12345"),
#     ]

#     result = manager.build_context(messages)

#     assert result.messages == messages[-4:]
#     assert result.estimated_tokens == 20


# def test_build_context_preserves_order():

#     token_counter = FakeTokenCounter()

#     budget = ContextBudget(
#         context_window=10,
#         reserved_output=0,
#         safety_margin_ratio=0,
#     )

#     manager = ContextManager(
#         token_counter=token_counter,
#         budget=budget,
#     )

#     messages = [
#         ChatMessage(role="user", content="11111"),
#         ChatMessage(role="assistant", content="22222"),
#         ChatMessage(role="user", content="33333"),
#     ]

#     result = manager.build_context(messages)

#     assert [message.content for message in result.messages] == [
#         "22222",
#         "33333",
#     ]


# def test_safety_margin_reduces_available_budget():

#     budget = ContextBudget(
#         context_window=100,
#         reserved_output=20,
#         safety_margin_ratio=0.10,
#     )

#     assert budget.safety_margin_tokens == 10
#     assert budget.available_input_tokens == 70


# def test_build_context_with_empty_messages():

#     token_counter = FakeTokenCounter()

#     budget = ContextBudget(
#         context_window=20,
#         reserved_output=0,
#         safety_margin_ratio=0,
#     )

#     manager = ContextManager(
#         token_counter=token_counter,
#         budget=budget,
#     )

#     result = manager.build_context([])

#     assert result.messages == []
#     assert result.estimated_tokens == 0


class FakeTokenCounter:
    def count_messages(self, messages):
        content_tokens = sum(len(message.content) for message in messages)

        return content_tokens + (10 if messages else 0)


def test_estimated_tokens_uses_full_context_count():

    token_counter = FakeTokenCounter()

    budget = ContextBudget(
        context_window=20,
        reserved_output=0,
        safety_margin_ratio=0,
    )

    manager = ContextManager(
        token_counter=token_counter,
        budget=budget,
    )

    messages = [
        ChatMessage(role="user", content="12345"),
        ChatMessage(role="assistant", content="12345"),
    ]

    result = manager.build_context(messages)

    assert result.messages == messages
    assert result.estimated_tokens == 20
