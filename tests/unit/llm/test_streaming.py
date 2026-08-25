import pytest

from app.domain.llm import ChatMessage, LLMRequest
from app.llm.mock_client import MockClient
from app.llm.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_mock_stream_chat_yields_words():
    client = MockClient()

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="hello world")],
    )

    chunks = []
    async for delta in client.stream_chat(request):
        chunks.append(delta)

    assert len(chunks) > 1
    assert "".join(chunks).strip() == "Mock hello world"


@pytest.mark.asyncio
async def test_mock_stream_chat_matches_chat():
    client = MockClient()

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="test")],
    )

    streamed = "".join([d async for d in client.stream_chat(request)]).strip()
    non_stream = (await client.chat(request)).content

    assert streamed == non_stream


def test_parse_stream_delta_extracts_content():
    data = '{"choices": [{"delta": {"content": "Hello"}}]}'
    assert OpenAIClient._parse_stream_delta(data) == "Hello"


def test_parse_stream_delta_extracts_reasoning_content():
    # Model reasoning (DeepSeek-V4) kirim reasoning_content dulu.
    data = '{"choices": [{"delta": {"reasoning_content": "We need"}}]}'
    assert OpenAIClient._parse_stream_delta(data) == "We need"


def test_parse_stream_delta_prefers_content_over_reasoning():
    data = '{"choices": [{"delta": {"reasoning_content": "think", "content": "answer"}}]}'
    assert OpenAIClient._parse_stream_delta(data) == "answer"


def test_parse_stream_delta_empty_choices():
    data = '{"choices": []}'
    assert OpenAIClient._parse_stream_delta(data) is None


def test_parse_stream_delta_invalid_json():
    # Baris aneh (bukan JSON) tidak boleh crash → None.
    assert OpenAIClient._parse_stream_delta("not json") is None
