from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from opentelemetry import trace

from app.core.observability.otel import get_tracer

_TRACER_NAME = "app.llm"


def _set_token_usage(span: trace.Span, usage) -> None:
    if usage is None:
        return

    span.set_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", usage.output_tokens)


@asynccontextmanager
async def instrument_llm_call(
    provider: str,
    model: str,
    operation: str,
    estimated_tokens: int | None = None,
) -> AsyncIterator[trace.Span]:
    """Wrap satu panggilan LLM dalam span OTel.

    Span: `llm.{provider}.{operation}` dengan atribut provider/model; token
    usage aktual di-set oleh caller lewat `span` yang di-yield (lihat
    `_set_token_usage`). `estimated_tokens` (tokenizer lokal) ikut dicatat
    sebagai atribut agar bisa dibandingkan dengan usage aktual di Jaeger.
    Exception menandai span error (`status` + `error.type`).
    """
    tracer = get_tracer(_TRACER_NAME)

    attributes = {
        "llm.provider": provider,
        "llm.model": model,
        "gen_ai.request.model": model,
    }
    if estimated_tokens is not None:
        attributes["llm.estimated.input_tokens"] = estimated_tokens

    with tracer.start_as_current_span(
        f"llm.{provider}.{operation}",
        attributes=attributes,
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            span.set_attribute("error.type", type(exc).__name__)
            raise
        else:
            span.set_status(trace.Status(trace.StatusCode.OK))
