import time

from opentelemetry import trace as otel_trace
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context.trace import clear_trace_id, create_trace_id, get_trace_id, set_trace_id
from app.core.logging.logger import logger
from app.core.metrics.http import http_request_duration_seconds, http_request_total


def _route_label(request) -> str:
    """Label path untuk metrik.

    Pakai template route (mis. `/api/chat/conversations/{conversation_id}`)
    supaya metrik tidak meledak oleh path tak dikenal dari scanner/bot —
    semua request yang tidak match route apa pun dikelompokkan sebagai
    `unmatched` (biasanya 404/405).
    """
    route = request.scope.get("route")
    if route is not None:
        return getattr(route, "path", None) or request.url.path
    return "unmatched"


class TraceMiddleware(BaseHTTPMiddleware):

    async def dispatch(
            self,
            request,
            call_next,
    ):

        client_trace_id = request.headers.get("X-Trace-Id")

        start = time.monotonic()

        if client_trace_id:
            set_trace_id(client_trace_id)
        else:
            create_trace_id()

        # Bridge trace id klien ke span OTel aktif (kalau ada), supaya bisa
        # dicari dari Jaeger via atribut client.trace_id.
        span = otel_trace.get_current_span()
        span_context = span.get_span_context()

        if span_context.is_valid and client_trace_id:
            span.set_attribute("client.trace_id", client_trace_id)

        logger.info(
            "http_request_started",
            method=request.method,
            path=request.url.path
        )

        try:

            response = await call_next(request)

            duration = time.monotonic() - start
            route_label = _route_label(request)

            http_request_total.labels(
                method=request.method,
                path=route_label,
                status_code=response.status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=request.method,
                path=route_label
            ).observe(duration)


            latency = (
                time.monotonic() - start
            ) * 1000

            logger.info(
                "http_request_completed",
                method=request.method,
                path=route_label,
                status_code=response.status_code,
                latency=round(latency,2),
            )

            # X-Trace-Id = trace id server (OTel, sama dengan di Jaeger).
            # X-Client-Trace-Id = trace id dari klien (echo).
            response.headers["X-Trace-Id"] = get_trace_id() or ""
            if client_trace_id:
                response.headers["X-Client-Trace-Id"] = client_trace_id

            return response

        finally:

            clear_trace_id()
