from fastapi import FastAPI

from app.api.router import api_router, root_router
from app.core.config.settings import get_settings
from app.core.exceptions.base import AppException
from app.core.exceptions.handlers import app_exception_handler
from app.core.lifespan import lifespan
from app.core.rate_limiter.http_store import InMemoryRateLimitStore
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.trace import TraceMiddleware

app = FastAPI(lifespan=lifespan)

settings = get_settings()

app.add_middleware(
    TraceMiddleware
)

# Rate limit semua request (in-memory per client IP).
# /metrics dikecualikan dari rate limit HTTP (sudah dilindungi API key).
rate_limit_store = InMemoryRateLimitStore(
    limit=settings.http_rate_limit.requests_per_minute,
)

app.add_middleware(
    RateLimitMiddleware,
    store=rate_limit_store,
    exclude_paths=("/metrics",),
)

app.add_exception_handler(
    AppException, 
    app_exception_handler
)

app.include_router(root_router)
app.include_router(api_router)
