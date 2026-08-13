from __future__ import annotations

import logging
import re

import httpx

from domain.entities.alert import Alert
from domain.entities.monitor_server import MonitorServer
from domain.entities.severity import Severity
from infrastructure.adapters.http_client import build_http_client, log_fetch_failed

CGI_SUFFIX = "/cgi-bin/status.cgi?host=all&servicestatustypes=253&limit=0"
ROW_RE = re.compile(
    r"class='(statusWARNING|statusCRITICAL)'.*?>(.*?)</td>",
    re.DOTALL,
)
TAG_RE = re.compile(r"<.*?>")


class NagiosCgiHttpClient:
    def __init__(
        self,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def fetch(self, server: MonitorServer) -> list[Alert]:
        url = f"{server.url.rstrip('/')}{CGI_SUFFIX}"
        client = build_http_client(server, self._timeout_seconds, self._transport)
        try:
            response = client.get(url)
            if response.status_code != 200:
                log_fetch_failed(
                    server,
                    error_type="http_status",
                    http_status=response.status_code,
                    exc_info=logging.getLogger(__name__).isEnabledFor(logging.DEBUG),
                )
                return []
            matches = ROW_RE.findall(response.text)
            alerts: list[Alert] = []
            for status_class, text in matches:
                clean_text = TAG_RE.sub("", text).strip()
                severity = "CRITICAL" if "CRITICAL" in status_class else "WARNING"
                alerts.append(
                    Alert(
                        server=server.name,
                        severity=Severity(severity),
                        alertname="NagiosAlert",
                        app="CGI Service",
                        desc=clean_text[:120],
                        status_text=clean_text,
                    )
                )
            return alerts
        except httpx.HTTPError as exc:
            log_fetch_failed(
                server,
                error_type=type(exc).__name__,
                exc_info=logging.getLogger(__name__).isEnabledFor(logging.DEBUG),
            )
            return []
        finally:
            client.close()
