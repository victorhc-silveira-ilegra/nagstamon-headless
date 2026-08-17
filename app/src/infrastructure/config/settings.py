from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from infrastructure.config.dotenv_loader import load_project_dotenv

DEFAULT_FILTER_WEEKDAYS = (0, 1, 2, 3, 4)
_WEEKDAY_ALIASES = {
    "0": 0,
    "mon": 0,
    "monday": 0,
    "seg": 0,
    "segunda": 0,
    "1": 1,
    "tue": 1,
    "tuesday": 1,
    "ter": 1,
    "terca": 1,
    "2": 2,
    "wed": 2,
    "wednesday": 2,
    "qua": 2,
    "quarta": 2,
    "3": 3,
    "thu": 3,
    "thursday": 3,
    "qui": 3,
    "quinta": 3,
    "4": 4,
    "fri": 4,
    "friday": 4,
    "sex": 4,
    "sexta": 4,
    "5": 5,
    "sat": 5,
    "saturday": 5,
    "sab": 5,
    "sabado": 5,
    "6": 6,
    "sun": 6,
    "sunday": 6,
    "dom": 6,
    "domingo": 6,
}


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


def _parse_hhmm(raw: str, name: str) -> time:
    parts = raw.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"{name} must be HH:MM")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise ValueError(f"{name} must be HH:MM") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"{name} must be HH:MM")
    return time(hour, minute)


def _parse_timezone(raw: str) -> str:
    name = raw.strip() or "America/Sao_Paulo"
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, KeyError, ValueError) as exc:
        raise ValueError("WINDOW_TIMEZONE must be a valid IANA timezone") from exc
    return name


def _parse_weekdays(raw: str) -> tuple[int, ...]:
    text = raw.strip()
    if not text:
        return DEFAULT_FILTER_WEEKDAYS
    seen: set[int] = set()
    days: list[int] = []
    for token in text.replace(";", ",").split(","):
        key = token.strip().lower()
        if not key:
            continue
        if key not in _WEEKDAY_ALIASES:
            raise ValueError(
                "WINDOW_DAYS must be weekdays (mon..sun, seg..dom or 0..6)"
            )
        day = _WEEKDAY_ALIASES[key]
        if day not in seen:
            seen.add(day)
            days.append(day)
    if not days:
        return DEFAULT_FILTER_WEEKDAYS
    return tuple(sorted(days))


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
    log_dir: Path | None
    dedup_enabled: bool
    dedup_window_minutes: int
    filter_window_enabled: bool
    filter_window_start: time
    filter_window_end: time
    filter_timezone: str
    filter_weekdays: tuple[int, ...]
    filter_hold_fast_seconds: int
    filter_hold_critical_seconds: int
    filter_hold_warning_seconds: int
    filter_duration_max_seconds: int
    sound_enabled: bool
    gchat_webhook_url: str
    dedup_ledger_path: Path | None

    @classmethod
    def from_env(cls) -> Settings:
        if not _parse_bool(os.environ.get("NAGSTAMON_DISABLE_DOTENV", "false")):
            load_project_dotenv(override=True)
        servers_dir = Path(
            os.environ.get("SERVERS_DIR", "/etc/nagstamon/servers")
        ).expanduser()
        proxy_addr = os.environ.get("PROXY_ADDR", "").strip()
        refresh_interval = _parse_positive_int(
            os.environ.get("REFRESH_INTERVAL_SECONDS", "30"),
            "REFRESH_INTERVAL_SECONDS",
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
        log_dir_raw = os.environ.get("LOG_DIR", "logs").strip()
        log_dir = Path(log_dir_raw).expanduser() if log_dir_raw else None
        dedup_enabled = _parse_bool(os.environ.get("DEDUP_ENABLED", "true"))
        dedup_window_minutes = _parse_positive_int(
            os.environ.get("DEDUP_WINDOW_MINUTES", "30"),
            "DEDUP_WINDOW_MINUTES",
        )
        filter_window_enabled = _parse_bool(os.environ.get("WINDOW_ENABLED", "true"))
        filter_window_start = _parse_hhmm(
            os.environ.get("WINDOW_START", "13:30").strip() or "13:30",
            "WINDOW_START",
        )
        filter_window_end = _parse_hhmm(
            os.environ.get("WINDOW_END", "18:00").strip() or "18:00",
            "WINDOW_END",
        )
        filter_timezone = _parse_timezone(os.environ.get("WINDOW_TIMEZONE", ""))
        filter_weekdays = _parse_weekdays(os.environ.get("WINDOW_DAYS", ""))
        filter_hold_fast_seconds = _parse_positive_int(
            os.environ.get("FILTER_HOLD_FAST_SECONDS", "600").strip() or "600",
            "FILTER_HOLD_FAST_SECONDS",
        )
        filter_hold_critical_seconds = _parse_positive_int(
            os.environ.get("FILTER_HOLD_CRITICAL_SECONDS", "900").strip() or "900",
            "FILTER_HOLD_CRITICAL_SECONDS",
        )
        filter_hold_warning_seconds = _parse_positive_int(
            os.environ.get("FILTER_HOLD_WARNING_SECONDS", "1200").strip() or "1200",
            "FILTER_HOLD_WARNING_SECONDS",
        )
        filter_duration_max_seconds = _parse_positive_int(
            os.environ.get("FILTER_DURATION_MAX_SECONDS", "86400").strip() or "86400",
            "FILTER_DURATION_MAX_SECONDS",
        )
        for hold_name, hold_value in (
            ("FILTER_HOLD_FAST_SECONDS", filter_hold_fast_seconds),
            ("FILTER_HOLD_CRITICAL_SECONDS", filter_hold_critical_seconds),
            ("FILTER_HOLD_WARNING_SECONDS", filter_hold_warning_seconds),
        ):
            if hold_value >= filter_duration_max_seconds:
                raise ValueError(
                    f"{hold_name} must be less than FILTER_DURATION_MAX_SECONDS"
                )
        sound_enabled = _parse_bool(os.environ.get("SOUND_ENABLED", "true"))
        gchat_webhook_url = os.environ.get("GCHAT_WEBHOOK_URL", "").strip()
        ledger_raw = os.environ.get("DEDUP_LEDGER_PATH", "").strip()
        dedup_ledger_path = Path(ledger_raw).expanduser() if ledger_raw else None
        return cls(
            servers_dir=servers_dir,
            proxy_addr=proxy_addr,
            refresh_interval=refresh_interval,
            http_timeout_seconds=timeout,
            http_max_workers=max_workers,
            log_level=log_level,
            log_format=log_format,
            log_file=log_file_raw or None,
            log_dir=log_dir,
            dedup_enabled=dedup_enabled,
            dedup_window_minutes=dedup_window_minutes,
            filter_window_enabled=filter_window_enabled,
            filter_window_start=filter_window_start,
            filter_window_end=filter_window_end,
            filter_timezone=filter_timezone,
            filter_weekdays=filter_weekdays,
            filter_hold_fast_seconds=filter_hold_fast_seconds,
            filter_hold_critical_seconds=filter_hold_critical_seconds,
            filter_hold_warning_seconds=filter_hold_warning_seconds,
            filter_duration_max_seconds=filter_duration_max_seconds,
            sound_enabled=sound_enabled,
            gchat_webhook_url=gchat_webhook_url,
            dedup_ledger_path=dedup_ledger_path,
        )
