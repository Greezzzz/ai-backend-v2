from contextvars import ContextVar
from uuid import uuid4

from opentelemetry import trace as otel_trace


_TRACE_ID: ContextVar[str | None] = ContextVar(
    "trace_id",
    default=None
)


def create_trace_id() -> str:
    trace_id = uuid4().hex
    _TRACE_ID.set(trace_id)
    return trace_id


def get_trace_id() -> str | None:
    """Trace id yang dipakai di log & header.

    Prioritas: OTel span aktif (trace id-nya sama dengan di Jaeger), fallback
    ke ContextVar custom (dipakai kalau OTel mati / span tidak aktif).
    """
    span = otel_trace.get_current_span()
    ctx = span.get_span_context()

    if ctx.is_valid:
        return format(ctx.trace_id, "032x")

    return _TRACE_ID.get()


def set_trace_id(trace_id: str) -> None:
    _TRACE_ID.set(trace_id)


def clear_trace_id() -> None:
    _TRACE_ID.set(None)
