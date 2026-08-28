from app.domain.llm import ChatMessage
from app.infrastructure.tokenizer.openai.token_counter import OpenAITokenCounter


def test_count_messages():
    counter = OpenAITokenCounter()

    messages = [
        ChatMessage(
            role="user",
            content="Hello",
        )
    ]

    result = counter.count_messages(messages)

    assert result > 0


def test_count_conversation_messages():
    counter = OpenAITokenCounter()

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
    counter = OpenAITokenCounter()

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

    base = OpenAITokenCounter(token_correction=0)
    corrected = OpenAITokenCounter(token_correction=79)

    assert corrected.count_messages(messages) == base.count_messages(messages) + 79


def test_gpt4o_model_uses_o200k_encoding():
    counter = OpenAITokenCounter(model="gpt-4o")

    assert counter._encoding.name == "o200k_base"


def test_gpt35_model_uses_cl100k_encoding():
    counter = OpenAITokenCounter(model="gpt-3.5-turbo")

    assert counter._encoding.name == "cl100k_base"


def test_deepseek_model_falls_back_to_cl100k():
    # Model OpenAI-compatible yang tidak dikenal tiktoken → cl100k_base (default aman).
    counter = OpenAITokenCounter(model="some-unknown-model")

    assert counter._encoding.name == "cl100k_base"
