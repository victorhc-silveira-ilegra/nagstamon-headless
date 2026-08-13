from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from infrastructure.config.dotenv_loader import load_project_dotenv


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_positive_int(raw: str, name: str) -> int:
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _parse_positive_float(raw: str, name: str) -> float:
    try:
        value = float(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    servers_dir: Path
    proxy_addr: str
    refresh_interval: int
    http_timeout_seconds: float
    http_max_workers: int
    log_level: str
    log_format: str
    log_file: str | None
    dedup_enabled: bool
    dedup_window_minutes: int

    @classmethod
    def from_env(cls) -> Settings:
        if not _parse_bool(os.environ.get("NAGSTAMON_DISABLE_DOTENV", "false")):
            load_project_dotenv(override=True)
        servers_dir = Path(
            os.environ.get("SERVERS_DIR", "/etc/nagstamon/servers")
        ).expanduser()
        proxy_addr = os.environ.get("PROXY_ADDR", "").strip()
        refresh_interval = _parse_positive_int(
            os.environ.get("REFRESH_INTERVAL", "30"),
            "REFRESH_INTERVAL",
        )
        timeout = _parse_positive_float(
            os.environ.get("HTTP_TIMEOUT_SECONDS", "5"),
            "HTTP_TIMEOUT_SECONDS",
        )
        max_workers = _parse_positive_int(
            os.environ.get("HTTP_MAX_WORKERS", "30"),
            "HTTP_MAX_WORKERS",
        )
        log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(
                "LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL"
            )
        log_format = os.environ.get("LOG_FORMAT", "text").strip().lower() or "text"
        if log_format not in {"text", "json"}:
            raise ValueError("LOG_FORMAT must be 'text' or 'json'")
        log_file_raw = os.environ.get("LOG_FILE", "").strip()
        dedup_enabled = _parse_bool(os.environ.get("DEDUP_ENABLED", "true"))
        dedup_window_minutes = _parse_positive_int(
            os.environ.get("DEDUP_WINDOW_MINUTES", "30"),
            "DEDUP_WINDOW_MINUTES",
        )
        return cls(
            servers_dir=servers_dir,
            proxy_addr=proxy_addr,
            refresh_interval=refresh_interval,
            http_timeout_seconds=timeout,
            http_max_workers=max_workers,
            log_level=log_level,
            log_format=log_format,
            log_file=log_file_raw or None,
            dedup_enabled=dedup_enabled,
            dedup_window_minutes=dedup_window_minutes,
        )
