"""
Centralized logging for the full-auto-agent app.
Use get_logger(__name__) in any module for a named logger that inherits this config.
"""
import logging
import sys
from pathlib import Path

# Default format: timestamp, level, name, message
DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Project logger name; child loggers will inherit config when we configure this
ROOT_LOGGER_NAME = "full_auto_agent"

# Only configured once
_configured = False


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given name (e.g. __name__). Configures root project logger on first use."""
    global _configured
    if not _configured:
        _configure()
        _configured = True
    if name.startswith(ROOT_LOGGER_NAME):
        return logging.getLogger(name)
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


def _configure(
    level: str | int | None = None,
    log_file: Path | str | None = None,
    fmt: str = DEFAULT_FORMAT,
    date_fmt: str = DEFAULT_DATE_FORMAT,
) -> None:
    """
    Configure the root project logger. Called automatically on first get_logger().
    Can be called early with custom level/file if needed.
    """
    import os

    level = level or os.environ.get("LOG_LEVEL", "INFO")
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    if log_file is None:
        log_file = os.environ.get("LOG_FILE")

    root = logging.getLogger(ROOT_LOGGER_NAME)
    root.setLevel(level)
    root.handlers.clear()

    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    # Console
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Optional file
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # Prevent propagation to the real root (avoids duplicate lines from libraries)
    root.propagate = False


def set_level(level: str | int) -> None:
    """Set the logging level for the root project logger (e.g. 'DEBUG', 'INFO')."""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger(ROOT_LOGGER_NAME).setLevel(level)
