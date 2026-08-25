from contextvars import ContextVar
from uuid import uuid4


_TRACE_ID: ContextVar[str | None] = ContextVar(
    "trace_id",
    default=None
)


def create_trace_id() -> str:
    trace_id = uuid4().hex
    _TRACE_ID.set(trace_id)
    return trace_id


def get_trace_id()-> str | None:
    return _TRACE_ID.get()


def set_trace_id(trace_id: str) -> None:
    _TRACE_ID.set(trace_id)


def clear_trace_id() -> None:
    _TRACE_ID.set(None)