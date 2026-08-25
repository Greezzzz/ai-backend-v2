from app.core.exceptions.base import AppException
from app.core.exceptions.error_codes import ErrorCode


class RateLimiterException(AppException):
    pass

class RateLimiterTimeoutException(RateLimiterException):

    def __init__(
            self,
            details: dict | None = None
    ):
        super().__init__(
            message = "Rate limit acquire timeout",
            code = ErrorCode.RATE_LIMITER_TIMEOUT,
            status_code = 504,
            details = details
        )