class AppException(Exception):

    def __init__(
            self,
            message: str,
            code: str,
            status_code: int,
            details: dict | None = None
    ):
        super().__init__(message)

        self.code = code
        self.status_code = status_code
        self.details = details
        self.message = message


    def with_context(self, **kwargs):
        merged = {
            **(self.details or {}),
            **kwargs
        }

        return self.__class__(
            message=self.message,
            code=self.code,
            status_code=self.status_code,
            details=merged
        )