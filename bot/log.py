"""Logging configuration for the CFB bot."""

import logging


def parse_log_level(level_str: str) -> int:
    """Convert a level name string to a logging level int, defaulting to INFO."""
    level = getattr(logging, level_str.upper(), None)
    if isinstance(level, int):
        return level
    return logging.INFO

_RESET = "\x1b[0m"
_LEVEL_COLORS = {
    logging.DEBUG: "\x1b[2m",     # dim
    logging.ERROR: "\x1b[31m",    # red
    logging.WARNING: "\x1b[33m",  # yellow
}


class ColoredFormatter(logging.Formatter):
    """Formatter that adds ANSI color to ERROR and WARNING level lines."""

    def __init__(self) -> None:
        super().__init__(fmt="%(asctime)s %(levelname)-8s %(name)s %(message)s",
                         datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        color = _LEVEL_COLORS.get(record.levelno)
        if color:
            return f"{color}{msg}{_RESET}"
        return msg
