from __future__ import annotations

import logging
from pathlib import Path

from presentation.logging.formatters import JsonSemanticFormatter, TextSemanticFormatter

_CONFIGURED = False


def setup_logging(
    *,
    level: str = "INFO",
    log_format: str = "text",
    log_file: str | None = None,
) -> None:
    global _CONFIGURED
    root = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    formatter: logging.Formatter
    if log_format.lower() == "json":
        formatter = JsonSemanticFormatter()
    else:
        formatter = TextSemanticFormatter()

    handlers: list[logging.Handler] = []
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root.handlers.clear()
    for handler in handlers:
        root.addHandler(handler)
    root.setLevel(numeric_level)

    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def reset_logging_state() -> None:
    global _CONFIGURED
    _CONFIGURED = False
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)
