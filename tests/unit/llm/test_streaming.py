import asyncio
import json

import pytest

from app.core.config.llm import (
    ChatSettings,
    HttpSettings,
    LimitSettings,
    LLMSettings,
)
from app.core.config.retry import RetrySettings
from app.domain.llm import ChatMessage, LLMRequest
from app.llm.mock_client import MockClient
from app.llm.openai_client import OpenAIClient


def _make_request() -> LLMRequest:
    return LLMRequest(messages=[ChatMessage(role="user", content="halo")])


class _FakeRateLimiter:
    async def acquire(self):
        return None


def _make_client(max_output_tokens: int = 4096, temperature: float = 0.7) -> OpenAIClient:
    settings = LLMSettings(
        api_key="test",
        base_url="https://api.test",
        http=HttpSettings(
            connect=10,
            write=30,
            read=30,
            stream_read=300,
            pool=30,
        ),
        chat=ChatSettings(
            model="deepseek-v4-flash",
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
        limit=LimitSettings(
            max_connections=100,
            max_keepalive_connections=20,
            keep_alive_expiry=30,
        ),
        retry=RetrySettings(
            max_attempt=3,
            base_delay=0.5,
            multiplier=2.0,
            max_delay=8.0,
            enable_jitter=True,
        ),
    )
    return OpenAIClient(http=None, settings=settings, retry_executor=None, rate_limiter=None)  # type: ignore[arg-type]


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


def test_parse_stream_usage_extracts_from_real_chunk_shape():
    # Chunk usage OpenAI/DeepSeek: punya `choices` (delta kosong) + `usage`.
    data = json.dumps(
        {
            "id": "chatcmpl-xyz",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {}}],
            "usage": {
                "prompt_tokens": 7,
                "completion_tokens": 387,
                "total_tokens": 394,
                "completion_tokens_details": {"reasoning_tokens": 320},
                "prompt_tokens_details": {"cached_tokens": 0},
            },
        }
    )

    usage = OpenAIClient._parse_stream_usage(data)

    assert usage is not None
    assert usage.input_tokens == 7
    assert usage.output_tokens == 387
    assert usage.total_tokens == 394


def test_parse_stream_usage_none_when_no_usage_field():
    assert OpenAIClient._parse_stream_usage(
        '{"choices": [{"delta": {"content": "halo"}}]}'
    ) is None
    assert OpenAIClient._parse_stream_usage("not json") is None


def test_stream_chat_captures_usage_anywhere_in_stream():
    client = _make_client()
    client._rate_limiter = _FakeRateLimiter()  # type: ignore[assignment]

    # Simulasikan chunk: delta → usage (tengah) → delta → [DONE].
    chunks = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"id": "x", "choices": [{"delta": {}}], "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
        "data: [DONE]",
    ]

    async def fake_send_stream(payload):
        for c in chunks:
            yield c

    client._send_stream = fake_send_stream  # type: ignore[method-assign]

    async def collect():
        return [d async for d in client.stream_chat(_make_request())]

    deltas = asyncio.run(collect())

    assert deltas == ["Hello", " world"]
    assert client.last_usage is not None
    assert client.last_usage.input_tokens == 5
    assert client.last_usage.output_tokens == 10
    assert client.last_usage.total_tokens == 15


def test_stream_chat_no_usage_leaves_last_usage_none():
    client = _make_client()
    client._rate_limiter = _FakeRateLimiter()  # type: ignore[assignment]

    chunks = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        "data: [DONE]",
    ]

    async def fake_send_stream(payload):
        for c in chunks:
            yield c

    client._send_stream = fake_send_stream  # type: ignore[method-assign]

    async def collect():
        return [d async for d in client.stream_chat(_make_request())]

    asyncio.run(collect())

    assert client.last_usage is None


def test_to_domain_prefers_content_over_reasoning():
    data = {
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "message": {
                    "content": "Jawaban akhir",
                    "reasoning_content": "Kita perlu berpikir dulu",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    response = _make_client()._to_domain(data)

    assert response.content == "Jawaban akhir"


def test_to_domain_falls_back_to_reasoning_when_content_empty():
    # DeepSeek-V4 bisa kirim `content` kosong dan jawaban di `reasoning_content`.
    data = {
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "message": {
                    "content": None,
                    "reasoning_content": "Kita perlu menjawab 'Halo'",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    response = _make_client()._to_domain(data)

    assert response.content == "Kita perlu menjawab 'Halo'"


def test_build_payload_includes_temperature_and_max_tokens():
    client = _make_client(max_output_tokens=4096, temperature=0.7)

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="halo")],
        temperature=0.3,
        max_tokens=2048,
    )

    payload = client._build_payload(request)

    assert payload["model"] == "deepseek-v4-flash"
    assert payload["max_tokens"] == 2048
    assert payload["temperature"] == 0.3
    assert payload["messages"] == [{"role": "user", "content": "halo"}]


def test_build_payload_falls_back_to_settings():
    client = _make_client(max_output_tokens=4096, temperature=0.7)

    request = LLMRequest(messages=[ChatMessage(role="user", content="halo")])

    payload = client._build_payload(request)

    assert payload["max_tokens"] == 4096
    assert payload["temperature"] == 0.7


def test_build_stream_payload_includes_temperature_and_max_tokens():
    client = _make_client(max_output_tokens=4096, temperature=0.7)

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="halo")],
        temperature=0.5,
        max_tokens=1000,
    )

    payload = client._build_stream_payload(request)

    assert payload["stream"] is True
    assert payload["max_tokens"] == 1000
    assert payload["temperature"] == 0.5
