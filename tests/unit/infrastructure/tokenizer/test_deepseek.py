from app.domain.llm import ChatMessage
from app.infrastructure.tokenizer.deepseek.v4.token_counter import (
    DeepSeekV4TokenCounter,
)


def test_count_messages():
    counter = DeepSeekV4TokenCounter()

    messages = [
        ChatMessage(
            role="user",
            content="Hello",
        )
    ]

    result = counter.count_messages(messages)

    assert result > 0


def test_count_conversation_messages():
    counter = DeepSeekV4TokenCounter()

    messages = [
        ChatMessage(
            role="user",
            content="Halo, aku Udinxxx",
        ),
        ChatMessage(
            role="assistant",
            content=(
                "Halo Udinxxx! Senang berkenalan denganmu. 😊\n\n"
                "Ada yang bisa aku bantu hari ini?"
            ),
        ),
        ChatMessage(
            role="user",
            content="siapa namaku tadi?",
        ),
    ]

    result = counter.count_messages(messages)

    assert result > 0


def test_count_messages_increases_with_history():
    counter = DeepSeekV4TokenCounter()

    messages = [
        ChatMessage(
            role="user",
            content="Hello",
        )
    ]

    initial_count = counter.count_messages(messages)

    messages.append(
        ChatMessage(
            role="user",
            content="How are you?",
        )
    )

    expanded_count = counter.count_messages(messages)

    assert expanded_count > initial_count


def test_token_correction_adds_fixed_offset():
    messages = [
        ChatMessage(
            role="user",
            content="Hello",
        )
    ]

    base = DeepSeekV4TokenCounter(token_correction=0)
    corrected = DeepSeekV4TokenCounter(token_correction=79)

    assert corrected.count_messages(messages) == base.count_messages(messages) + 79
