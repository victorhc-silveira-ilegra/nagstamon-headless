from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable, Sequence
from zoneinfo import ZoneInfo

from application.ports.alert_sink import AlertSinkPort
from application.use_cases.poll_monitors import PollCycleResult, PollMonitorsUseCase
from domain.services.alert_filter import AlertFilterPolicy
from infrastructure.adapters.alertmanager_http import AlertmanagerHttpClient
from infrastructure.adapters.composite_alert_sink import CompositeAlertSink
from infrastructure.adapters.composite_monitor_client import CompositeMonitorClient
from infrastructure.adapters.file_alert_dispatch_ledger import FileAlertDispatchLedger
from infrastructure.adapters.google_chat_http import GoogleChatWebhookSink
from infrastructure.adapters.in_memory_alert_dispatch_ledger import (
    InMemoryAlertDispatchLedger,
)
from infrastructure.adapters.ini_server_config import IniServerConfigAdapter
from infrastructure.adapters.nagios_cgi_http import NagiosCgiHttpClient
from infrastructure.adapters.popen_alert_sound import PopenAlertSound
from infrastructure.adapters.stdout_alert_sink import StdoutAlertSink
from infrastructure.adapters.system_clock import SystemClock
from infrastructure.config.settings import Settings
from infrastructure.logging import (
    MONITOR_CONFIG_EMPTY,
    POLL_ALERT_SKIPPED_DUPLICATE,
    POLL_CYCLE_FAILED,
    POLL_CYCLE_FINISHED,
    POLL_CYCLE_SKIPPED_IN_FLIGHT,
    POLL_CYCLE_STARTED,
    WORKER_BOOT_FAILED,
    WORKER_STARTED,
    log_event,
)
from presentation.logging import setup_logging
from presentation.worker.cycle_guard import CycleGuard

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nagstamon-headless",
        description="Daemon headless de alertas efetivos (Alertmanager / Nagios CGI)",
    )
    parser.add_argument("--max-cycles", type=int, default=None)
    return parser


def _alert_sink(settings: Settings) -> AlertSinkPort:
    zone = ZoneInfo(settings.filter_timezone)
    stdout = StdoutAlertSink(timezone=zone)
    if not settings.gchat_webhook_url:
        return stdout
    return CompositeAlertSink(
        stdout,
        GoogleChatWebhookSink(
            settings.gchat_webhook_url,
            timeout_seconds=settings.http_timeout_seconds,
            proxy=settings.proxy_addr,
            timezone=zone,
        ),
    )


def _dispatch_ledger(
    settings: Settings,
) -> FileAlertDispatchLedger | InMemoryAlertDispatchLedger | None:
    if not settings.dedup_enabled:
        return None
    if settings.dedup_ledger_path is not None:
        return FileAlertDispatchLedger(settings.dedup_ledger_path)
    return InMemoryAlertDispatchLedger()


def build_use_case(settings: Settings) -> PollMonitorsUseCase:
    timeout = settings.http_timeout_seconds
    sound = PopenAlertSound() if settings.sound_enabled else None
    return PollMonitorsUseCase(
        server_config=IniServerConfigAdapter(
            servers_dir=settings.servers_dir,
            default_proxy=settings.proxy_addr,
        ),
        monitor_client=CompositeMonitorClient(
            alertmanager=AlertmanagerHttpClient(timeout_seconds=timeout),
            nagios=NagiosCgiHttpClient(timeout_seconds=timeout),
            max_workers=settings.http_max_workers,
        ),
        alert_sink=_alert_sink(settings),
        clock=SystemClock(),
        filter_policy=AlertFilterPolicy(
            window_start=settings.filter_window_start,
            window_end=settings.filter_window_end,
            timezone=ZoneInfo(settings.filter_timezone),
            min_duration_seconds=settings.filter_duration_min_seconds,
            max_duration_seconds=settings.filter_duration_max_seconds,
        ),
        dispatch_ledger=_dispatch_ledger(settings),
        alert_sound=sound,
        dedup_window_minutes=settings.dedup_window_minutes,
    )


def run_cycle(use_case: PollMonitorsUseCase) -> PollCycleResult:
    log_event(logger, logging.INFO, POLL_CYCLE_STARTED)
    started_at = time.monotonic()
    try:
        result = use_case.execute()
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            POLL_CYCLE_FAILED,
            error_type=type(exc).__name__,
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )
        raise
    if result.skipped_duplicate_count:
        log_event(
            logger,
            logging.INFO,
            POLL_ALERT_SKIPPED_DUPLICATE,
            skipped_count=result.skipped_duplicate_count,
        )
    log_event(
        logger,
        logging.INFO,
        POLL_CYCLE_FINISHED,
        servers_count=result.servers_count,
        alerts_count=result.alerts_count,
        claimed_count=result.claimed_count,
        skipped_duplicate_count=result.skipped_duplicate_count,
        duration_ms=int((time.monotonic() - started_at) * 1000),
        status="ok",
    )
    return result


def _emit_boot_failed(exc: BaseException) -> None:
    setup_logging(level="INFO", log_format="text", log_file=None)
    log_event(
        logger,
        logging.ERROR,
        WORKER_BOOT_FAILED,
        error_type=type(exc).__name__,
    )


def run(
    argv: Sequence[str] | None = None,
    *,
    use_case: PollMonitorsUseCase | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    settings: Settings | None = None,
    cycle_guard: CycleGuard | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        resolved = settings or Settings.from_env()
        setup_logging(
            level=resolved.log_level,
            log_format=resolved.log_format,
            log_file=resolved.log_file,
        )
        resolved_use_case = use_case or build_use_case(resolved)
    except Exception as exc:
        _emit_boot_failed(exc)
        return 1
    log_event(
        logger,
        logging.INFO,
        WORKER_STARTED,
        refresh_interval=resolved.refresh_interval,
        dedup_enabled=resolved.dedup_enabled,
        dedup_window_minutes=resolved.dedup_window_minutes,
        log_format=resolved.log_format,
    )
    guard = cycle_guard or CycleGuard()
    cycles_run = 0
    config_empty_emitted = False
    while True:
        if not guard.try_enter():
            log_event(logger, logging.WARNING, POLL_CYCLE_SKIPPED_IN_FLIGHT)
            cycles_run += 1
            if args.max_cycles is not None and cycles_run >= args.max_cycles:
                return 0
            sleeper(resolved.refresh_interval)
            continue
        try:
            try:
                result = run_cycle(resolved_use_case)
            except Exception:
                return 1
            if not config_empty_emitted:
                if result.servers_count == 0:
                    log_event(
                        logger,
                        logging.WARNING,
                        MONITOR_CONFIG_EMPTY,
                        servers_count=0,
                    )
                config_empty_emitted = True
            cycles_run += 1
            if args.max_cycles is not None and cycles_run >= args.max_cycles:
                return 0
            sleeper(resolved.refresh_interval)
        finally:
            guard.exit()


def main() -> None:
    raise SystemExit(run())
