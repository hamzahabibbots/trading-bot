"""
Logging configuration for the trading bot.
Sets up both console and file logging with structured formatting.
"""

import logging
import os
from datetime import datetime


def setup_logging(log_dir: str = "logs", level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure and return the application logger.

    Creates a logger with two handlers:
      - Console handler: INFO-level, concise format
      - File handler: DEBUG-level, detailed format with timestamps

    Args:
        log_dir: Directory to store log files. Created if it doesn't exist.
        level: Root logging level.

    Returns:
        Configured logger instance.
    """
    os.makedirs(log_dir, exist_ok=True)

    log_filename = datetime.now().strftime("trading_bot_%Y%m%d_%H%M%S.log")
    log_filepath = os.path.join(log_dir, log_filename)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(level)

    # Prevent duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # ── File handler (DEBUG level — captures everything) ──
    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    # ── Console handler (INFO level — user-facing) ──
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized → {log_filepath}")
    return logger
