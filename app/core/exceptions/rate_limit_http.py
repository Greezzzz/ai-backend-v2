from app.core.exceptions.base import AppException
from app.core.exceptions.error_codes import ErrorCode


class RateLimitExceededException(AppException):
    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Rate limit exceeded",
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details=details,
        )
