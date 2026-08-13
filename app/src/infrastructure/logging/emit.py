from __future__ import annotations

import logging
from typing import Any


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    exc_info: bool = False,
    **fields: Any,
) -> None:
    payload = {"event": event, **fields}
    logger.log(level, event, extra={"semantic": payload}, exc_info=exc_info)
