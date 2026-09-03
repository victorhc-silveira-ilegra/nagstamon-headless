from __future__ import annotations

import logging
import os
import time
from collections.abc import Mapping
from pathlib import Path

from application.use_cases.ping_monitors import PingMonitorsResult, PingMonitorsUseCase
from infrastructure.adapters.http_monitor_probe import HttpMonitorProbeAdapter
from infrastructure.adapters.ini_server_config import IniServerConfigAdapter
from infrastructure.config.settings import Settings
from infrastructure.logging import (
    MONITOR_PING_FAILED,
    MONITOR_PING_FINISHED,
    MONITOR_PING_STARTED,
    WORKER_BOOT_FAILED,
    log_event,
)
from presentation.logging import setup_logging

logger = logging.getLogger(__name__)


def resolve_servers_dir(
    settings: Settings, environ: Mapping[str, str] | None = None
) -> Path:
    env = os.environ if environ is None else environ
    host = env.get("HOST_SERVERS_DIR", "").strip()
    if host:
        path = Path(host).expanduser()
        if path.is_dir():
            return path
    return settings.servers_dir


def build_use_case(
    settings: Settings, servers_dir: Path | None = None
) -> PingMonitorsUseCase:
    if servers_dir is not None:
        directory = servers_dir
    else:
        directory = resolve_servers_dir(settings)
    return PingMonitorsUseCase(
        server_config=IniServerConfigAdapter(
            servers_dir=directory,
            default_proxy=settings.proxy_addr,
        ),
        probe=HttpMonitorProbeAdapter(
            timeout_seconds=settings.http_timeout_seconds,
        ),
        max_workers=settings.http_max_workers,
    )


def _emit_boot_failed(exc: BaseException) -> None:
    setup_logging(level="INFO", log_format="text", log_file=None)
    log_event(
        logger,
        logging.ERROR,
        WORKER_BOOT_FAILED,
        error_type=type(exc).__name__,
    )


def run(
    *,
    use_case: PingMonitorsUseCase | None = None,
    settings: Settings | None = None,
) -> int:
    try:
        resolved = settings or Settings.from_env()
        setup_logging(
            level=resolved.log_level,
            log_format=resolved.log_format,
            log_file=resolved.log_file,
        )
        directory = resolve_servers_dir(resolved)
        resolved_use_case = use_case or build_use_case(resolved, directory)
    except Exception as exc:
        _emit_boot_failed(exc)
        return 1
    log_event(
        logger,
        logging.INFO,
        MONITOR_PING_STARTED,
        servers_dir=str(directory),
    )
    started_at = time.monotonic()
    try:
        result = resolved_use_case.execute()
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            MONITOR_PING_FAILED,
            error_type=type(exc).__name__,
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )
        return 1
    _emit_finished(result, started_at)
    return 0


def _emit_finished(result: PingMonitorsResult, started_at: float) -> None:
    log_event(
        logger,
        logging.INFO,
        MONITOR_PING_FINISHED,
        servers_count=result.servers_count,
        reachable=result.reachable,
        unreachable=result.unreachable,
        updated=result.updated,
        unchanged=result.unchanged,
        duration_ms=int((time.monotonic() - started_at) * 1000),
        status="ok",
    )


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
