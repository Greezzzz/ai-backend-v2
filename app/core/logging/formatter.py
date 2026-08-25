import json
import logging

STANDARD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "taskName",
    "asctime"
}

class JsonFormatter(logging.Formatter):

    def format(
        self,
        record: logging.LogRecord
    ) -> str :

        log = {
            "timestamps" : record.created,
            "level" : record.levelname,
            "logger" : record.name,
            "event" : record.getMessage(),
        }

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in STANDARD_FIELDS
        }

        log.update(extras)

        if record.exc_info:
            log["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            log,
            ensure_ascii=False
        )