from app.core.exceptions.base import AppException
from app.core.exceptions.error_codes import ErrorCode


class BusinessException(AppException):
    pass


class BusinessValidationException(BusinessException):

    def __init__(
            self,
            message: str,
            status_code: int = 400,
            code: str = ErrorCode.BUSINESS_ERROR,
            details: dict | None = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details
        )