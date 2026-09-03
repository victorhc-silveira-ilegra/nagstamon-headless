from __future__ import annotations

import os
from datetime import time
from pathlib import Path

import pytest

from application.use_cases.ping_monitors import PingMonitorsResult
from infrastructure.config.settings import Settings
from infrastructure.logging.events import (
    MONITOR_PING_FAILED,
    MONITOR_PING_FINISHED,
    MONITOR_PING_STARTED,
    WORKER_BOOT_FAILED,
)
from presentation.cli.ping import build_use_case, main, resolve_servers_dir, run
from presentation.logging.config import reset_logging_state


def _captured(capsys: pytest.CaptureFixture[str]) -> str:
    streams = capsys.readouterr()
    return f"{streams.out}{streams.err}"


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        servers_dir=tmp_path,
        proxy_addr="",
        refresh_interval=1,
        http_timeout_seconds=5.0,
        http_max_workers=2,
        log_level="INFO",
        log_format="text",
        log_file=None,
        log_dir=None,
        dedup_enabled=True,
        dedup_window_minutes=30,
        filter_window_enabled=True,
        filter_window_start=time(13, 30),
        filter_window_end=time(18, 0),
        filter_window_allow_past_active_alerts=False,
        filter_timezone="America/Sao_Paulo",
        filter_weekdays=(0, 1, 2, 3, 4),
        filter_hold_fast_seconds=600,
        filter_hold_critical_seconds=900,
        filter_hold_warning_seconds=1200,
        filter_duration_max_seconds=86400,
        sound_enabled=False,
        gchat_webhook_url="",
        dedup_ledger_path=None,
    )


class FakeUseCase:
    def __init__(
        self,
        result: PingMonitorsResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or PingMonitorsResult(0, 0, 0, 0, 0)
        self.error = error
        self.calls = 0

    def execute(self) -> PingMonitorsResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


def test_resolve_servers_dir_host_override(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    docker = tmp_path / "docker"
    docker.mkdir()
    settings = _settings(docker)
    assert resolve_servers_dir(settings, {"HOST_SERVERS_DIR": str(host)}) == host
    missing = tmp_path / "missing"
    assert resolve_servers_dir(settings, {"HOST_SERVERS_DIR": str(missing)}) == docker
    assert resolve_servers_dir(settings, {}) == docker


def test_run_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    reset_logging_state()
    fake = FakeUseCase(
        PingMonitorsResult(
            servers_count=2,
            reachable=1,
            unreachable=1,
            updated=1,
            unchanged=1,
        )
    )
    code = run(use_case=fake, settings=_settings(tmp_path))  # type: ignore[arg-type]
    assert code == 0
    captured = _captured(capsys)
    assert MONITOR_PING_STARTED in captured
    assert MONITOR_PING_FINISHED in captured
    assert "reachable=1" in captured
    reset_logging_state()


def test_run_execute_failed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    reset_logging_state()
    import logging

    logging.getLogger("presentation.cli.ping").setLevel(logging.DEBUG)
    code = run(
        use_case=FakeUseCase(error=RuntimeError("boom")),  # type: ignore[arg-type]
        settings=_settings(tmp_path),
    )
    assert code == 1
    assert MONITOR_PING_FAILED in _captured(capsys)
    reset_logging_state()


def test_run_boot_failed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reset_logging_state()
    monkeypatch.setenv("REFRESH_INTERVAL_SECONDS", "0")
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    assert run() == 1
    assert WORKER_BOOT_FAILED in _captured(capsys)
    reset_logging_state()


def test_build_use_case_empty(tmp_path: Path) -> None:
    result = build_use_case(_settings(tmp_path)).execute()
    assert result.servers_count == 0


def test_build_use_case_explicit_servers_dir(tmp_path: Path) -> None:
    host = tmp_path / "explicit"
    host.mkdir()
    docker = tmp_path / "docker"
    docker.mkdir()
    result = build_use_case(_settings(docker), servers_dir=host).execute()
    assert result.servers_count == 0


def test_build_use_case_host_servers_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = tmp_path / "host"
    host.mkdir()
    (host / "server_am.conf").write_text(
        "[Server]\nenabled=False\nmonitor_url=http://am.example\ntype=alertmanager\n",
        encoding="utf-8",
    )
    docker = tmp_path / "docker"
    docker.mkdir()
    monkeypatch.setenv("HOST_SERVERS_DIR", str(host))
    monkeypatch.setattr(
        "presentation.cli.ping.HttpMonitorProbeAdapter.probe",
        lambda self, server: True,
    )
    result = build_use_case(_settings(docker)).execute()
    assert result.reachable == 1
    assert result.updated == 1
    text = (host / "server_am.conf").read_text(encoding="utf-8")
    assert "enabled=True" in text


def test_main_exits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "presentation.cli.ping.Settings.from_env",
        lambda: _settings(tmp_path),
    )
    monkeypatch.setattr(
        "presentation.cli.ping.build_use_case",
        lambda settings, servers_dir=None: FakeUseCase(),
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_resolve_servers_dir_uses_environ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = tmp_path / "from-env"
    host.mkdir()
    monkeypatch.setenv("HOST_SERVERS_DIR", str(host))
    assert resolve_servers_dir(_settings(tmp_path)) == host
    assert "HOST_SERVERS_DIR" in os.environ
