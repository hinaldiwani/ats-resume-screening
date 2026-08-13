"""
app/core/logging_config.py

Centralized logging setup using loguru.
Called once at application startup (see app/main.py -> on_startup).

No business logic — configuration only.
"""

import sys
import os
from loguru import logger

from app.core.config import get_settings

settings = get_settings()


def configure_logging() -> None:
    """
    Configures loguru sinks:
      - Console sink (colored, human-readable) for local development
      - Rotating file sink under LOG_DIR/LOG_FILE for persistent logs

    Call once from main.py's startup event. Safe to call multiple times
    (loguru handlers are cleared first to avoid duplicate log lines on reload).
    """
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    log_path = os.path.join(settings.LOG_DIR, settings.LOG_FILE)

    logger.remove()  # clear default handler to avoid duplicate console output

    # Console sink
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # Rotating file sink
    logger.add(
        log_path,
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,  # process-safe, useful once Celery workers log too
        backtrace=False,
        diagnose=False,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.info(f"Logging configured | env={settings.APP_ENV} | level={settings.LOG_LEVEL}")


__all__ = ["configure_logging", "logger"]
