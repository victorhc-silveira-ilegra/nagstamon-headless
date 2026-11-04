from __future__ import annotations

import logging
import socket

import httpx

from domain.entities.monitor_server import MonitorServer
from infrastructure.logging import MONITOR_FETCH_FAILED, log_event, redact_url

USER_AGENT = {"User-Agent": "Nagstamon-Docker/4.0"}

logger = logging.getLogger(__name__)


class DnsResolvingProxyTransport(httpx.HTTPTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        try:
            ip = socket.gethostbyname(host)
            if ip != host:
                request.headers.setdefault("Host", host)
                request.url = request.url.copy_with(host=ip)
        except (OSError, socket.gaierror):
            pass
        return super().handle_request(request)


def build_http_client(
    server: MonitorServer,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    auth: tuple[str, str] | None = None
    if server.username and server.password:
        auth = (server.username, server.password)
    resolved_transport = transport
    if resolved_transport is None and server.proxy:
        resolved_transport = DnsResolvingProxyTransport(
            proxy=server.proxy, verify=False
        )
    return httpx.Client(
        timeout=timeout_seconds,
        proxy=None if resolved_transport is not None else (server.proxy or None),
        auth=auth,
        transport=resolved_transport,
        headers=USER_AGENT,
        verify=False,
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
