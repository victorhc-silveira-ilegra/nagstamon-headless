from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAILY_LOG_PREFIX = "nagstamon-"
DAILY_LOG_SUFFIX = ".log"
DEFAULT_LOG_TIMEZONE = "America/Sao_Paulo"


def resolve_log_timezone(name: str | None) -> ZoneInfo:
    raw = (name or "").strip() or DEFAULT_LOG_TIMEZONE
    try:
        return ZoneInfo(raw)
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        return ZoneInfo(DEFAULT_LOG_TIMEZONE)


def daily_log_name(day: date) -> str:
    return f"{DAILY_LOG_PREFIX}{day.isoformat()}{DAILY_LOG_SUFFIX}"


def stale_daily_log_paths(logs_dir: Path, today: date) -> list[Path]:
    keep = daily_log_name(today)
    if not logs_dir.is_dir():
        return []
    stale: list[Path] = []
    for child in logs_dir.iterdir():
        if child.name in {".gitkeep", keep}:
            continue
        stale.append(child)
    return stale


class DailyLogFile:
    def __init__(
        self,
        directory: Path,
        timezone: ZoneInfo,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._directory = directory
        self._timezone = timezone
        self._clock = clock
        self._day: date | None = None
        self._handle: TextIO | None = None

    def _now(self) -> datetime:
        if self._clock is not None:
            return self._clock()
        return datetime.now(self._timezone)

    def write(self, data: str) -> int:
        if not data:
            return 0
        self._ensure()
        assert self._handle is not None
        written = self._handle.write(data)
        self._handle.flush()
        return written

    def flush(self) -> None:
        if self._handle is not None:
            self._handle.flush()

    def close(self) -> None:
        if self._handle is None:
            return
        self._handle.close()
        self._handle = None
        self._day = None

    def _ensure(self) -> None:
        today = self._now().astimezone(self._timezone).date()
        if self._handle is not None and today == self._day:
            return
        self.close()
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / daily_log_name(today)
        self._handle = path.open("a", encoding="utf-8")
        self._day = today


class TeeStream:
    def __init__(self, primary: TextIO, secondary: DailyLogFile) -> None:
        self._primary = primary
        self._secondary = secondary

    def write(self, data: str) -> int:
        self._primary.write(data)
        self._secondary.write(data)
        return len(data)

    def flush(self) -> None:
        self._primary.flush()
        self._secondary.flush()

    def isatty(self) -> bool:
        checker = getattr(self._primary, "isatty", None)
        if checker is None:
            return False
        return bool(checker())

    @property
    def encoding(self) -> str:
        return str(getattr(self._primary, "encoding", None) or "utf-8")

    @property
    def errors(self) -> str | None:
        value = getattr(self._primary, "errors", None)
        return value if isinstance(value, str) else None

    @property
    def closed(self) -> bool:
        return bool(getattr(self._primary, "closed", False))


def attach_daily_stdio(
    directory: Path,
    timezone: ZoneInfo,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> DailyLogFile:
    daily = DailyLogFile(directory, timezone)
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    sys.stdout = TeeStream(out, daily)
    sys.stderr = TeeStream(err, daily)
    return daily
