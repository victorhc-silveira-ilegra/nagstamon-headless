from __future__ import annotations

import json
import logging
from typing import Any


def _semantic_fields(record: logging.LogRecord) -> dict[str, Any]:
    semantic = getattr(record, "semantic", None)
    if isinstance(semantic, dict):
        return dict(semantic)
    return {"event": record.getMessage()}


class TextSemanticFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = _semantic_fields(record)
        event = str(fields.pop("event", record.getMessage()))
        parts = [
            self.formatTime(record, self.datefmt),
            record.levelname,
            f"event={event}",
        ]
        for key in sorted(fields):
            value = fields[key]
            parts.append(f"{key}={value}")
        return " ".join(parts)


class JsonSemanticFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = _semantic_fields(record)
        payload = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            **fields,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)
