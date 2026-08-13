from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        return urlunsplit((parts.scheme, parts.netloc, path, "***", ""))
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def truncate_preview(value: str, max_len: int = 80) -> str:
    text = value.strip()
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3]}..."
