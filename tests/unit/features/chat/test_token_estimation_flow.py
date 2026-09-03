"""Alur `estimated_tokens` dari ChatService → LLMRequest.

Estimasi tokenizer lokal (dari ContextManager) harus sampai ke request LLM
supaya client bisa mencatatnya sebagai atribut span (`llm.estimated.input_tokens`)
untuk dibandingkan dengan usage aktual provider di Jaeger.
"""
from collections.abc import AsyncIterator

from app.domain.llm import ChatMessage, LLMResponse
from app.features.chat.service import ChatService

MESSAGES = [ChatMessage(role="user", content="halo")]


class _CapturingClient:
    """Client fake yang menangkap request terakhir yang diterima."""

    def __init__(self) -> None:
        self.last_request = None

    async def chat(self, request) -> LLMResponse:
        self.last_request = request
        return LLMResponse(content="halo juga", model="mock")

    async def stream_chat(self, request) -> AsyncIterator[str]:
        self.last_request = request
        yield "halo"
        yield " juga"


async def test_ask_forwards_estimated_tokens():
    client = _CapturingClient()
    service = ChatService(client=client)  # type: ignore[arg-type]

    await service.ask(MESSAGES, estimated_tokens=123)

    assert client.last_request is not None
    assert client.last_request.estimated_tokens == 123


async def test_stream_ask_forwards_estimated_tokens():
    client = _CapturingClient()
    service = ChatService(client=client)  # type: ignore[arg-type]

    async for _ in service.stream_ask(MESSAGES, estimated_tokens=456):
        pass

    assert client.last_request is not None
    assert client.last_request.estimated_tokens == 456


async def test_estimated_tokens_defaults_to_none():
    client = _CapturingClient()
    service = ChatService(client=client)  # type: ignore[arg-type]

    await service.ask(MESSAGES)

    assert client.last_request is not None
    assert client.last_request.estimated_tokens is None
