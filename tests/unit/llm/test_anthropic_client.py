import json

import httpx
import pytest

from app.core.config.llm import (
    ChatSettings,
    HttpSettings,
    LimitSettings,
    LLMSettings,
)
from app.core.config.retry import RetrySettings
from app.core.config.settings import Settings
from app.core.resources import Resources
from app.domain.llm import ChatMessage, LLMRequest
from app.llm.anthropic_client import AnthropicClient
from app.llm.factory import get_chat_client
from app.llm.mock_client import MockClient


def _make_client() -> AnthropicClient:
    settings = LLMSettings(
        api_key="test-key",
        base_url="https://api.anthropic.com",
        http=HttpSettings(
            connect=10,
            write=30,
            read=30,
            stream_read=300,
            pool=30,
        ),
        chat=ChatSettings(
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            max_output_tokens=4096,
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
    return AnthropicClient(http=None, settings=settings, retry_executor=None, rate_limiter=None)  # type: ignore[arg-type]


def test_build_payload_removes_system_role():
    client = _make_client()

    request = LLMRequest(
        messages=[
            ChatMessage(role="system", content="Kamu asisten yang ramah"),
            ChatMessage(role="user", content="halo"),
        ]
    )

    payload = client._build_payload(request)

    assert payload["model"] == "claude-3-5-sonnet-20241022"
    assert payload["system"] == "Kamu asisten yang ramah"
    assert payload["messages"] == [{"role": "user", "content": "halo"}]
    assert payload["max_tokens"] == 4096
    # Temperature tidak disertakan kalau request tidak mensetnya (API Anthropic nullable).
    assert "temperature" not in payload


def test_build_payload_prefers_request_max_tokens_and_temperature():
    client = _make_client()

    request = LLMRequest(
        messages=[ChatMessage(role="user", content="halo")],
        max_tokens=512,
        temperature=0.2,
    )

    payload = client._build_payload(request)

    assert payload["max_tokens"] == 512
    assert payload["temperature"] == 0.2


def test_build_stream_payload_enables_stream():
    client = _make_client()

    request = LLMRequest(messages=[ChatMessage(role="user", content="halo")])

    payload = client._build_stream_payload(request)

    assert payload["stream"] is True
    assert payload["max_tokens"] == 4096


@pytest.mark.parametrize(
    "line,expected",
    [
        ('{"type":"content_block_delta","delta":{"text":"Hello"}}', "Hello"),
        ('{"type":"content_block_delta","delta":{"type":"text_delta","text":"Hi"}}', "Hi"),
        ('{"type":"message_start","message":{"id":"m1"}}', None),
        ('{"type":"message_stop"}', None),
        ("not json", None),
        ('{"type":"content_block_delta","delta":{}}', None),
    ],
)
def test_parse_stream_event(line, expected):
    assert AnthropicClient._parse_stream_event(line) == expected


def test_to_domain_maps_anthropic_response():
    data = {
        "model": "claude-3-5-sonnet-20241022",
        "content": [
            {"type": "text", "text": "Ini jawaban"},
            {"type": "text", "text": " tambahan"},
        ],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 12, "output_tokens": 5},
    }

    response = AnthropicClient._to_domain(data)

    assert response.content == "Ini jawaban tambahan"
    assert response.model == "claude-3-5-sonnet-20241022"
    assert response.finish_reason == "end_turn"
    assert response.usage.input_tokens == 12
    assert response.usage.output_tokens == 5
    assert response.usage.total_tokens == 17


def test_headers_use_x_api_key():
    client = _make_client()
    headers = client._headers()

    assert headers["x-api-key"] == "test-key"
    assert headers["anthropic-version"] == "2023-06-01"
    assert headers["Content-Type"] == "application/json"
    assert "Authorization" not in headers


def test_parse_stream_usage_from_message_start():
    event = json.dumps(
        {
            "type": "message_start",
            "message": {
                "id": "msg_1",
                "usage": {"input_tokens": 12, "output_tokens": 5},
            },
        }
    )

    usage = AnthropicClient._parse_stream_usage(event)

    assert usage is not None
    assert usage.input_tokens == 12
    assert usage.output_tokens == 5
    assert usage.total_tokens == 17


def test_parse_stream_usage_none_for_other_events():
    assert AnthropicClient._parse_stream_usage(
        '{"type": "content_block_delta", "delta": {"text": "halo"}}'
    ) is None
    assert AnthropicClient._parse_stream_usage("not json") is None


@pytest.mark.asyncio
async def test_mock_stream_contract():
    # Sanity: MockClient tetap memenuhi LLMProtocol (dipakai di test_stream_api).
    client = MockClient()
    request = LLMRequest(messages=[ChatMessage(role="user", content="halo")])
    streamed = "".join([d async for d in client.stream_chat(request)]).strip()
    assert streamed == "Mock halo"


def _make_settings(provider: str) -> Settings:
    return Settings(
        chat_provider=provider,
        chat_api_key="k",
        chat_model="m",
        chat_base_url="https://api.test",
        chat_temp=0.7,
        chat_context_window=128000,
        chat_max_output_tokens=4096,
        chat_token_correction=0,
        chat_conn_timeout=10,
        chat_write_timeout=30,
        chat_read_timeout=30,
        chat_pool_timeout=30,
        chat_max_connections=100,
        chat_max_keepalive_connections=20,
        chat_keep_alive_expiry=30,
        chat_retry_max_attempt=3,
        chat_retry_base_delay=0.5,
        chat_retry_multiplier=2.0,
        chat_retry_max_delay=8.0,
        chat_retry_enable_jitter=True,
        chat_rate_limit_capacity=10,
        chat_rate_limit_refill_per_second=2,
        chat_rate_limit_acquire_timeout=5,
        http_rate_limit_requests_per_minute=60,
    )


def _make_factory_client(provider: str):
    settings = _make_settings(provider)
    resources = Resources(
        settings=settings,
        http_client=httpx.AsyncClient(),
    )
    return get_chat_client(resources=resources, rate_limiter=None)


@pytest.mark.asyncio
async def test_factory_dispatch_openai():
    client = await _make_factory_client("openai")

    from app.llm.openai_client import OpenAIClient

    assert isinstance(client, OpenAIClient)


@pytest.mark.asyncio
async def test_factory_dispatch_anthropic():
    client = await _make_factory_client("anthropic")

    assert isinstance(client, AnthropicClient)


@pytest.mark.asyncio
async def test_factory_unknown_provider_raises():
    with pytest.raises(ValueError):
        await _make_factory_client("groq")