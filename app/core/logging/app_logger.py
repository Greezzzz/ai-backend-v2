import logging
from typing import Any

from app.core.context.trace import get_trace_id


class AppLogger:

    def __init__(
            self,
            logger: logging.Logger
    ):
        self._logger = logger

    def _log(
        self,
        level: int,
        event: str,
        exc_info: bool = False,
        **kwargs: Any,    
    ) -> None:

        extra = {
            "trace_id": get_trace_id(),
            **kwargs
        }

        self._logger.log(
            level,
            event,
            extra=extra,
            exc_info=exc_info
        )

    def info(
        self,
        event: str,
        **kwargs: Any,
    ) -> None:
        self._log(logging.INFO, event, **kwargs)

    def warning(
        self,
        event: str,
        **kwargs: Any,
    ) -> None:
        self._log(logging.WARNING, event, **kwargs)

    def error(
        self,
        event: str,
        exc_info: bool = False,
        **kwargs: Any,
    ) -> None:
        self._log(logging.ERROR, event, exc_info, **kwargs)

    def debug(
        self,
        event: str,
        **kwargs: Any,
    ) -> None:
        self._log(logging.DEBUG, event, **kwargs)