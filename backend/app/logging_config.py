"""Logging setup. User text (posts, chat messages) must never be logged, except by the
app.transcript logger, which records chat exchanges on purpose."""

import logging
import os

MAX_ERROR_CHARS = 300


def configure_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if level not in logging.getLevelNamesMapping():
        level = "INFO"
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )


def describe_error(exc: BaseException) -> str:
    """Short, single-line error summary: type, HTTP status if any, truncated message."""
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    message = " ".join(str(exc).split())[:MAX_ERROR_CHARS]
    head = type(exc).__name__ + (f" status={status}" if status else "")
    return f"{head}: {message}"
