from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.core.exceptions.base import AppException
from app.core.schemas.error_response import ErrorResponse


async def app_exception_handler(
        request: Request, 
        exc: AppException
    ):

    response = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=exc.details
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(exclude_none=True)
    )