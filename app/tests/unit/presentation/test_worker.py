from __future__ import annotations

from datetime import time
from pathlib import Path
from threading import Event, Thread

import pytest

from application.use_cases.poll_monitors import PollCycleResult
from infrastructure.adapters.composite_alert_sink import CompositeAlertSink
from infrastructure.adapters.file_alert_dispatch_ledger import FileAlertDispatchLedger
from infrastructure.adapters.in_memory_alert_dispatch_ledger import (
    InMemoryAlertDispatchLedger,
)
from infrastructure.config.settings import Settings
from infrastructure.logging.events import (
    MONITOR_CONFIG_EMPTY,
    POLL_ALERT_SKIPPED_DUPLICATE,
    POLL_CYCLE_FAILED,
    POLL_CYCLE_FINISHED,
    POLL_CYCLE_SKIPPED_IN_FLIGHT,
    POLL_CYCLE_STARTED,
    WORKER_BOOT_FAILED,
    WORKER_STARTED,
)
from presentation.logging.config import reset_logging_state
from presentation.worker.cycle_guard import CycleGuard
from presentation.worker.main import build_use_case, main, run, run_cycle


def _captured(capsys: pytest.CaptureFixture[str]) -> str:
    streams = capsys.readouterr()
    return f"{streams.out}{streams.err}"


class FakeUseCase:
    def __init__(
        self,
        result: PollCycleResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or PollCycleResult(servers_count=1, alerts_count=0)
        self.error = error
        self.calls = 0

    def execute(self) -> PollCycleResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


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
        dedup_enabled=True,
        dedup_window_minutes=30,
        filter_window_start=time(13, 30),
        filter_window_end=time(18, 0),
        filter_timezone="America/Sao_Paulo",
        filter_duration_min_seconds=600,
        filter_duration_max_seconds=86400,
        sound_enabled=False,
        gchat_webhook_url="",
        dedup_ledger_path=None,
    )


def test_build_use_case_empty_dir(tmp_path: Path) -> None:
    use_case = build_use_case(_settings(tmp_path))
    result = use_case.execute()
    assert result.servers_count == 0
    assert result.alerts_count == 0


def test_build_use_case_dedup_disabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    disabled = Settings(
        servers_dir=settings.servers_dir,
        proxy_addr=settings.proxy_addr,
        refresh_interval=settings.refresh_interval,
        http_timeout_seconds=settings.http_timeout_seconds,
        http_max_workers=settings.http_max_workers,
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file,
        dedup_enabled=False,
        dedup_window_minutes=settings.dedup_window_minutes,
        filter_window_start=settings.filter_window_start,
        filter_window_end=settings.filter_window_end,
        filter_timezone=settings.filter_timezone,
        filter_duration_min_seconds=settings.filter_duration_min_seconds,
        filter_duration_max_seconds=settings.filter_duration_max_seconds,
        sound_enabled=False,
        gchat_webhook_url="",
        dedup_ledger_path=None,
    )
    use_case = build_use_case(disabled)
    result = use_case.execute()
    assert result.skipped_duplicate_count == 0
    assert result.claimed_count == 0


def test_build_use_case_sound_enabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    enabled = Settings(
        servers_dir=settings.servers_dir,
        proxy_addr=settings.proxy_addr,
        refresh_interval=settings.refresh_interval,
        http_timeout_seconds=settings.http_timeout_seconds,
        http_max_workers=settings.http_max_workers,
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file,
        dedup_enabled=settings.dedup_enabled,
        dedup_window_minutes=settings.dedup_window_minutes,
        filter_window_start=settings.filter_window_start,
        filter_window_end=settings.filter_window_end,
        filter_timezone=settings.filter_timezone,
        filter_duration_min_seconds=settings.filter_duration_min_seconds,
        filter_duration_max_seconds=settings.filter_duration_max_seconds,
        sound_enabled=True,
        gchat_webhook_url="",
        dedup_ledger_path=None,
    )
    use_case = build_use_case(enabled)
    result = use_case.execute()
    assert result.alerts_count == 0


def test_build_use_case_gchat_enabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    enabled = Settings(
        servers_dir=settings.servers_dir,
        proxy_addr=settings.proxy_addr,
        refresh_interval=settings.refresh_interval,
        http_timeout_seconds=settings.http_timeout_seconds,
        http_max_workers=settings.http_max_workers,
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file,
        dedup_enabled=settings.dedup_enabled,
        dedup_window_minutes=settings.dedup_window_minutes,
        filter_window_start=settings.filter_window_start,
        filter_window_end=settings.filter_window_end,
        filter_timezone=settings.filter_timezone,
        filter_duration_min_seconds=settings.filter_duration_min_seconds,
        filter_duration_max_seconds=settings.filter_duration_max_seconds,
        sound_enabled=False,
        gchat_webhook_url="https://chat.googleapis.com/v1/spaces/x/messages?key=k",
        dedup_ledger_path=None,
    )
    use_case = build_use_case(enabled)
    assert isinstance(use_case._alert_sink, CompositeAlertSink)
    result = use_case.execute()
    assert result.alerts_count == 0


def test_build_use_case_file_ledger(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with_file = Settings(
        servers_dir=settings.servers_dir,
        proxy_addr=settings.proxy_addr,
        refresh_interval=settings.refresh_interval,
        http_timeout_seconds=settings.http_timeout_seconds,
        http_max_workers=settings.http_max_workers,
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file,
        dedup_enabled=True,
        dedup_window_minutes=settings.dedup_window_minutes,
        filter_window_start=settings.filter_window_start,
        filter_window_end=settings.filter_window_end,
        filter_timezone=settings.filter_timezone,
        filter_duration_min_seconds=settings.filter_duration_min_seconds,
        filter_duration_max_seconds=settings.filter_duration_max_seconds,
        sound_enabled=False,
        gchat_webhook_url="",
        dedup_ledger_path=tmp_path / "dispatch-ledger.json",
    )
    use_case = build_use_case(with_file)
    assert isinstance(use_case._dispatch_ledger, FileAlertDispatchLedger)
    memory = build_use_case(_settings(tmp_path))
    assert isinstance(memory._dispatch_ledger, InMemoryAlertDispatchLedger)


def test_run_max_cycles_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    reset_logging_state()
    fake = FakeUseCase()
    code = run(
        ["--max-cycles", "1"],
        use_case=fake,  # type: ignore[arg-type]
        settings=_settings(tmp_path),
    )
    assert code == 0
    assert fake.calls == 1
    captured = _captured(capsys)
    assert WORKER_STARTED in captured
    assert POLL_CYCLE_STARTED in captured
    assert POLL_CYCLE_FINISHED in captured
    assert "duration_ms=" in captured
    assert "skipped_duplicate_count=" in captured
    assert MONITOR_CONFIG_EMPTY not in captured
    reset_logging_state()


def test_run_two_cycles_calls_sleeper(tmp_path: Path) -> None:
    slept: list[float] = []
    fake = FakeUseCase()
    code = run(
        ["--max-cycles", "2"],
        use_case=fake,  # type: ignore[arg-type]
        settings=_settings(tmp_path),
        sleeper=slept.append,
    )
    assert code == 0
    assert fake.calls == 2
    assert slept == [1]


def test_run_infinite_until_sleeper_stops(tmp_path: Path) -> None:
    fake = FakeUseCase()

    def _stop(_interval: float) -> None:
        raise RuntimeError("stop")

    with pytest.raises(RuntimeError, match="stop"):
        run(
            [],
            use_case=fake,  # type: ignore[arg-type]
            settings=_settings(tmp_path),
            sleeper=_stop,
        )
    assert fake.calls == 1


def test_run_cycle_failure_returns_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reset_logging_state()
    fake = FakeUseCase(error=RuntimeError("boom"))
    code = run(
        ["--max-cycles", "1"],
        use_case=fake,  # type: ignore[arg-type]
        settings=_settings(tmp_path),
    )
    assert code == 1
    assert POLL_CYCLE_FAILED in _captured(capsys)
    reset_logging_state()


def test_run_settings_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reset_logging_state()
    monkeypatch.setenv("REFRESH_INTERVAL", "0")
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    assert run(["--max-cycles", "1"]) == 1
    assert WORKER_BOOT_FAILED in _captured(capsys)
    reset_logging_state()


def test_run_cycle_success_direct() -> None:
    fake = FakeUseCase(PollCycleResult(servers_count=2, alerts_count=3))
    result = run_cycle(fake)  # type: ignore[arg-type]
    assert result.alerts_count == 3


def test_main_exits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "presentation.worker.main.Settings.from_env",
        lambda: _settings(tmp_path),
    )
    monkeypatch.setattr(
        "presentation.worker.main.build_use_case",
        lambda settings: FakeUseCase(),
    )
    monkeypatch.setattr("sys.argv", ["nagstamon-headless", "--max-cycles", "1"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_run_cycle_debug_exc_info() -> None:
    import logging

    logging.getLogger("presentation.worker.main").setLevel(logging.DEBUG)
    fake = FakeUseCase(error=RuntimeError("debug"))
    with pytest.raises(RuntimeError):
        run_cycle(fake)  # type: ignore[arg-type]


def test_run_logs_skipped_duplicates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reset_logging_state()
    fake = FakeUseCase(
        PollCycleResult(
            servers_count=1,
            alerts_count=2,
            claimed_count=0,
            skipped_duplicate_count=2,
        )
    )
    code = run(
        ["--max-cycles", "1"],
        use_case=fake,  # type: ignore[arg-type]
        settings=_settings(tmp_path),
    )
    assert code == 0
    captured = _captured(capsys)
    assert POLL_ALERT_SKIPPED_DUPLICATE in captured
    reset_logging_state()


def test_run_skips_in_flight_cycle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reset_logging_state()
    started = Event()
    hold = Event()
    settings = _settings(tmp_path)
    guard = CycleGuard()

    class BlockingUseCase:
        def execute(self) -> PollCycleResult:
            started.set()
            hold.wait(timeout=5)
            return PollCycleResult(servers_count=0, alerts_count=0)

    def _first() -> None:
        try:
            run(
                [],
                use_case=BlockingUseCase(),  # type: ignore[arg-type]
                settings=settings,
                cycle_guard=guard,
                sleeper=lambda _interval: (_ for _ in ()).throw(RuntimeError("stop")),
            )
        except RuntimeError:
            return

    thread = Thread(target=_first)
    thread.start()
    assert started.wait(timeout=5)
    code = run(
        ["--max-cycles", "1"],
        use_case=FakeUseCase(),  # type: ignore[arg-type]
        settings=settings,
        cycle_guard=guard,
    )
    assert code == 0
    captured = _captured(capsys)
    assert POLL_CYCLE_SKIPPED_IN_FLIGHT in captured
    assert "WARNING event=poll.cycle.skipped_in_flight" in captured
    with pytest.raises(RuntimeError, match="after-skip"):
        run(
            [],
            use_case=FakeUseCase(),  # type: ignore[arg-type]
            settings=settings,
            cycle_guard=guard,
            sleeper=lambda _interval: (_ for _ in ()).throw(RuntimeError("after-skip")),
        )
    hold.set()
    thread.join(timeout=5)
    reset_logging_state()


def test_cycle_guard_rejects_second_enter() -> None:
    guard = CycleGuard()
    assert guard.try_enter() is True
    assert guard.try_enter() is False
    guard.exit()
    assert guard.try_enter() is True
    guard.exit()


def test_skip_in_flight_continues_until_max_cycles(tmp_path: Path) -> None:
    reset_logging_state()
    guard = CycleGuard()
    assert guard.try_enter() is True
    slept: list[float] = []
    code = run(
        ["--max-cycles", "2"],
        use_case=FakeUseCase(),  # type: ignore[arg-type]
        settings=_settings(tmp_path),
        cycle_guard=guard,
        sleeper=slept.append,
    )
    assert code == 0
    assert slept == [1]
    guard.exit()
    reset_logging_state()


def test_run_emits_config_empty_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reset_logging_state()
    fake = FakeUseCase(PollCycleResult(servers_count=0, alerts_count=0))
    code = run(
        ["--max-cycles", "2"],
        use_case=fake,  # type: ignore[arg-type]
        settings=_settings(tmp_path),
        sleeper=lambda _interval: None,
    )
    assert code == 0
    captured = _captured(capsys)
    assert captured.count(MONITOR_CONFIG_EMPTY) == 1
    assert "WARNING event=monitor.config.empty" in captured
    reset_logging_state()
