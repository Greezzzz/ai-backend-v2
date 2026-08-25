from app.core.exceptions.base import AppException
from app.core.exceptions.error_codes import ErrorCode


class AuthException(AppException):
    pass


class InvalidCredentialsException(AuthException):
    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Invalid credentials",
            code=ErrorCode.INVALID_CREDENTIALS,
            status_code=401,
            details=details,
        )


class AuthenticationRequiredException(AuthException):
    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Authentication required",
            code=ErrorCode.AUTHENTICATION_ERROR,
            status_code=401,
            details=details,
        )


class InvalidApiKeyException(AuthException):
    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Invalid API key",
            code=ErrorCode.AUTHENTICATION_ERROR,
            status_code=401,
            details=details,
        )


class UserAlreadyExistsException(AuthException):
    def __init__(self, details: dict | None = None):
        super().__init__(
            message="User already exists",
            code=ErrorCode.USER_ALREADY_EXISTS,
            status_code=409,
            details=details,
        )
