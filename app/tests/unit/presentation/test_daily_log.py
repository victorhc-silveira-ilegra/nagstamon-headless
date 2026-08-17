from __future__ import annotations

import io
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from presentation.logging.daily import (
    DailyLogFile,
    TeeStream,
    attach_daily_stdio,
    daily_log_name,
    resolve_log_timezone,
    stale_daily_log_paths,
)


class _BareStream:
    def __init__(self) -> None:
        self.chunks: list[str] = []

    def write(self, data: str) -> int:
        self.chunks.append(data)
        return len(data)

    def flush(self) -> None:
        return None


class _TtyStream(_BareStream):
    def isatty(self) -> bool:
        return True


class _ClosedStream(_BareStream):
    closed = True


def test_resolve_log_timezone() -> None:
    assert resolve_log_timezone(None).key == "America/Sao_Paulo"
    assert resolve_log_timezone("  ").key == "America/Sao_Paulo"
    assert resolve_log_timezone("UTC").key == "UTC"
    assert resolve_log_timezone("Nope/Nope").key == "America/Sao_Paulo"


def test_resolve_log_timezone_value_and_key_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = ZoneInfo

    def fake(name: str) -> ZoneInfo:
        if name == "Boom/Zone":
            raise ValueError("bad")
        if name == "Key/Zone":
            raise KeyError(name)
        return real(name)

    monkeypatch.setattr("presentation.logging.daily.ZoneInfo", fake)
    assert resolve_log_timezone("Boom/Zone").key == "America/Sao_Paulo"
    assert resolve_log_timezone("Key/Zone").key == "America/Sao_Paulo"


def test_daily_log_name_and_stale_paths(tmp_path: Path) -> None:
    today = date(2026, 8, 17)
    keep = tmp_path / daily_log_name(today)
    keep.write_text("keep", encoding="utf-8")
    gitkeep = tmp_path / ".gitkeep"
    gitkeep.write_text("", encoding="utf-8")
    old = tmp_path / daily_log_name(date(2026, 8, 16))
    old.write_text("old", encoding="utf-8")
    extra = tmp_path / "other.log"
    extra.write_text("x", encoding="utf-8")
    stale = {path.name for path in stale_daily_log_paths(tmp_path, today)}
    assert stale == {old.name, extra.name}
    assert stale_daily_log_paths(tmp_path / "missing", today) == []


def test_daily_log_file_writes_flushes_and_rolls(tmp_path: Path) -> None:
    zone = ZoneInfo("UTC")
    current = datetime(2026, 8, 17, 23, 0, tzinfo=zone)

    def clock() -> datetime:
        return current

    daily = DailyLogFile(tmp_path, zone, clock=clock)
    daily.flush()
    daily.close()
    assert daily.write("") == 0
    assert daily.write("first\n") == 6
    first = tmp_path / "nagstamon-2026-08-17.log"
    assert first.read_text(encoding="utf-8") == "first\n"
    daily.flush()
    current = datetime(2026, 8, 18, 0, 1, tzinfo=zone)
    assert daily.write("second\n") == 7
    second = tmp_path / "nagstamon-2026-08-18.log"
    assert first.read_text(encoding="utf-8") == "first\n"
    assert second.read_text(encoding="utf-8") == "second\n"
    daily.close()


def test_tee_stream_and_attach_daily_stdio(tmp_path: Path) -> None:
    zone = ZoneInfo("UTC")
    daily = DailyLogFile(
        tmp_path,
        zone,
        clock=lambda: datetime(2026, 8, 17, tzinfo=zone),
    )
    primary = io.StringIO()
    tee = TeeStream(primary, daily)
    tee.write("hello\n")
    tee.flush()
    assert primary.getvalue() == "hello\n"
    assert tee.encoding
    assert tee.errors in {None, "strict"}
    assert tee.closed is False
    assert tee.isatty() is False
    tty = TeeStream(_TtyStream(), daily)  # type: ignore[arg-type]
    assert tty.isatty() is True
    closed = TeeStream(_ClosedStream(), daily)  # type: ignore[arg-type]
    assert closed.closed is True
    bare = TeeStream(_BareStream(), daily)  # type: ignore[arg-type]
    assert bare.isatty() is False
    assert bare.encoding == "utf-8"
    assert bare.errors is None
    original_out = sys.stdout
    original_err = sys.stderr
    buffer = io.StringIO()
    live = tmp_path / "live"
    try:
        attached = attach_daily_stdio(live, zone, stdout=buffer, stderr=buffer)
        print("snap", flush=True)
        attached.close()
    finally:
        sys.stdout = original_out
        sys.stderr = original_err
    assert "snap" in buffer.getvalue()
    files = list(live.glob("nagstamon-*.log"))
    assert len(files) == 1
    assert "snap" in files[0].read_text(encoding="utf-8")
