from prometheus_client import Gauge

rate_limiter_tokens_available = Gauge(
    "rate_limiter_tokens_available",
    "Number of available tokens in the rate limiter",
)