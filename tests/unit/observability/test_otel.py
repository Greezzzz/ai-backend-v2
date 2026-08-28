import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.core.observability.llm import _set_token_usage, instrument_llm_call

# Provider global hanya boleh di-set SEKALI (OTel raise kalau di-override),
# jadi setup di module level, bukan per-test.
_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)


@pytest.fixture
def span_exporter():
    _exporter.clear()
    yield _exporter
    _exporter.clear()


@pytest.mark.asyncio
async def test_instrument_llm_call_sets_attributes(span_exporter):
    async with instrument_llm_call(
        provider="openai", model="gpt-4o", operation="chat"
    ):
        pass

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]

    assert span.name == "llm.openai.chat"
    assert span.attributes["llm.provider"] == "openai"
    assert span.attributes["llm.model"] == "gpt-4o"
    assert span.attributes["gen_ai.request.model"] == "gpt-4o"
    assert span.status.status_code == trace.StatusCode.OK


@pytest.mark.asyncio
async def test_instrument_llm_call_sets_token_usage(span_exporter):
    async with instrument_llm_call(
        provider="anthropic", model="claude-3-5", operation="chat"
    ) as span:
        _set_token_usage(
            span,
            type("Usage", (), {"input_tokens": 10, "output_tokens": 5})(),
        )

    spans = span_exporter.get_finished_spans()
    span = spans[0]

    assert span.attributes["gen_ai.usage.input_tokens"] == 10
    assert span.attributes["gen_ai.usage.output_tokens"] == 5


@pytest.mark.asyncio
async def test_instrument_llm_call_marks_error(span_exporter):
    with pytest.raises(RuntimeError, match="boom"):
        async with instrument_llm_call(
            provider="openai", model="gpt-4o", operation="stream"
        ):
            raise RuntimeError("boom")

    spans = span_exporter.get_finished_spans()
    span = spans[0]

    assert span.status.status_code == trace.StatusCode.ERROR
    assert span.attributes["error.type"] == "RuntimeError"
    assert len(span.events) >= 1  # exception event direkam
