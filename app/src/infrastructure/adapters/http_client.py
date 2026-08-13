from __future__ import annotations

import logging

import httpx

from domain.entities.monitor_server import MonitorServer
from infrastructure.logging import MONITOR_FETCH_FAILED, log_event, redact_url

USER_AGENT = {"User-Agent": "Nagstamon-Docker/4.0"}

logger = logging.getLogger(__name__)


def build_http_client(
    server: MonitorServer,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    auth: tuple[str, str] | None = None
    if server.username and server.password:
        auth = (server.username, server.password)
    return httpx.Client(
        timeout=timeout_seconds,
        proxy=server.proxy or None,
        auth=auth,
        transport=transport,
        headers=USER_AGENT,
    )


def log_fetch_failed(
    server: MonitorServer,
    *,
    error_type: str,
    http_status: int | None = None,
    exc_info: bool = False,
) -> None:
    fields: dict[str, object] = {
        "server_name": server.name,
        "monitor_host": redact_url(server.url),
        "error_type": error_type,
    }
    if http_status is not None:
        fields["http_status"] = http_status
    log_event(
        logger,
        logging.WARNING,
        MONITOR_FETCH_FAILED,
        exc_info=exc_info,
        **fields,
    )
