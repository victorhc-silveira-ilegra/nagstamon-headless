from __future__ import annotations

import logging

import httpx

from domain.entities.monitor_server import MonitorServer
from infrastructure.adapters.http_client import build_http_client
from infrastructure.adapters.nagios_cgi_http import CGI_SUFFIX
from infrastructure.logging import MONITOR_PING_FAILED, log_event, redact_url

logger = logging.getLogger(__name__)
_UNSUPPORTED = ("zabbix", "icinga", "centreon", "checkmk")


class HttpMonitorProbeAdapter:
    def __init__(
        self,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def probe(self, server: MonitorServer) -> bool:
        if self._is_unsupported(server):
            self._log_failed(server, error_type="unsupported")
            return False
        url = self._probe_url(server)
        client = build_http_client(server, self._timeout_seconds, self._transport)
        try:
            response = client.get(url)
            if 200 <= response.status_code < 300:
                return True
            self._log_failed(
                server,
                error_type="http_status",
                http_status=response.status_code,
            )
            return False
        except httpx.HTTPError as exc:
            self._log_failed(
                server,
                error_type=type(exc).__name__,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            return False
        finally:
            client.close()

    @staticmethod
    def _is_unsupported(server: MonitorServer) -> bool:
        haystack = f"{server.server_type} {server.name}".lower()
        return any(token in haystack for token in _UNSUPPORTED)

    @staticmethod
    def _probe_url(server: MonitorServer) -> str:
        if server.is_alertmanager:
            if server.url.endswith("/api/v2/alerts"):
                return server.url
            return f"{server.url.rstrip('/')}/api/v2/alerts"
        return f"{server.url.rstrip('/')}{CGI_SUFFIX}"

    @staticmethod
    def _log_failed(
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
            MONITOR_PING_FAILED,
            exc_info=exc_info,
            **fields,
        )
