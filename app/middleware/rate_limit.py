import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging.logger import logger
from app.core.rate_limiter.http_store import InMemoryRateLimitStore


class RateLimitMiddleware(BaseHTTPMiddleware):

    def __init__(
        self,
        app,
        store: InMemoryRateLimitStore,
        exclude_paths: tuple[str, ...] = (),
    ):
        super().__init__(app)
        self._store = store
        self._exclude_paths = exclude_paths

    def _client_key(self, request) -> str:
        # Identity sederhana: IP client. Nanti bisa diganti user id (Fase B+).
        forwarded = request.headers.get("X-Forwarded-For")

        if forwarded:
            return forwarded.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    async def dispatch(self, request, call_next):
        path = request.url.path

        if path.startswith(self._exclude_paths):
            return await call_next(request)

        key = self._client_key(request)

        if not self._store.is_allowed(key):
            logger.warning(
                "http_rate_limit_exceeded",
                client=key,
                path=path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded",
                    "details": None,
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
