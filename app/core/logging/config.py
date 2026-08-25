import logging
import sys

from app.core.logging.formatter import JsonFormatter


def setup_logging():

    handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(
        JsonFormatter()
    )

    logger = logging.getLogger()

    logger.handlers.clear()

    logger.addHandler(handler)

    logger.setLevel(logging.INFO)