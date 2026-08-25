from app.core.exceptions.base import AppException
from app.core.exceptions.error_codes import ErrorCode


class LLMException(AppException):
    pass


class LLMTimeoutException(LLMException):
    def __init__(self, details: dict | None = None):
        super().__init__(
            message="LLM request timed out",
            code= ErrorCode.LLM_TIMEOUT,
            status_code=504,
            details=details
        )

class LLMRateLimitException(LLMException):
    def __init__(self, details: dict | None = None):
        super().__init__(
            message="LLM request rate limit exceeded",
            code= ErrorCode.LLM_RATE_LIMIT,
            status_code=429,
            details=details
        )

class LLmAuthenticationException(LLMException):
    def __init__(self, details: dict | None = None):
        super().__init__(
            message="LLM authentication failed",
            code= ErrorCode.LLM_AUTHENTICATION_ERROR,
            status_code=401,
            details=details
        )

class LLMProviderException(LLMException):
    def __init__(self, details: dict | None = None):
        super().__init__(
            message="LLM provider error",
            code= ErrorCode.LLM_PROVIDER_ERROR,
            status_code=502,
            details=details
        )