import logging

from app.core.logging.app_logger import AppLogger

logger = AppLogger(
    logging.getLogger("ai-backend")
)