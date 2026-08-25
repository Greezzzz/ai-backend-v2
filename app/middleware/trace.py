import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context.trace import clear_trace_id, create_trace_id, set_trace_id
from app.core.logging.logger import logger
from app.core.metrics.http import http_request_duration_seconds, http_request_total


class TraceMiddleware(BaseHTTPMiddleware):

    async def dispatch(
            self,
            request,
            call_next,
    ):

        trace_id = request.headers.get(
            "X-Trace-id"
        )

        start = time.monotonic()

        if trace_id:
            set_trace_id(trace_id)
        else:
            trace_id = create_trace_id()

        logger.info(
            "http_request_started",
            method = request.method,
            path=request.url.path
        )

        try:

            response = await call_next(request)

            duration = time.monotonic() - start

            http_request_total.labels(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=request.method,
                path=request.url.path
            ).observe(duration)


            latency = (
                time.monotonic() - start
            ) * 1000

            logger.info(
                "http_request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency=round(latency,2),
            )

            response.headers["X-Trace-Id"] = trace_id

            return response

        finally:

            clear_trace_id()