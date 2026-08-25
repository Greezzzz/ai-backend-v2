from app.core.rate_limiter.limiter import RateLimiter
from app.core.rate_limiter.token_bucket import TokenBucketRateLimiter
from fastapi import Depends
from app.core.resources import Resources
from app.core.config.dependencies import get_resources

def get_rate_limiter(
    resources: Resources = Depends(get_resources)
) -> RateLimiter:
    return TokenBucketRateLimiter(
        resources.settings.rate_limit
    )