from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import httpx

from domain.entities.alert import Alert
from domain.entities.monitor_server import MonitorServer
from domain.entities.severity import Severity
from infrastructure.adapters.http_client import build_http_client, log_fetch_failed


def _as_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value if item)
    if value:
        return (str(value),)
    return ()


def _parse_starts_at(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_alert(server: MonitorServer, item: dict[str, Any]) -> Alert:
    labels = _as_dict(item.get("labels"))
    annotations = _as_dict(item.get("annotations"))
    status = _as_dict(item.get("status"))
    alertname = str(labels.get("alertname") or "N/A")
    desc = str(
        annotations.get("title") or annotations.get("message") or "Sem descricao"
    )
    app = str(labels.get("application") or labels.get("instance") or "N/A")
    severity_raw = str(labels.get("severity") or "WARNING")
    starts_at = _parse_starts_at(item.get("startsAt"))
    status_text = f"{alertname} {desc}"
    return Alert(
        server=server.name,
        severity=Severity(severity_raw),
        alertname=alertname,
        app=app,
        desc=desc,
        status_text=status_text,
        starts_at=starts_at,
        alert_state=str(status.get("state") or ""),
        silenced_by=_as_tuple(status.get("silencedBy")),
        inhibited_by=_as_tuple(status.get("inhibitedBy")),
    )


class AlertmanagerHttpClient:
    def __init__(
        self,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def fetch(self, server: MonitorServer) -> list[Alert]:
        url = (
            server.url
            if server.url.endswith("/api/v2/alerts")
            else f"{server.url.rstrip('/')}/api/v2/alerts"
        )
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
            payload = response.json()
            if not isinstance(payload, list):
                log_fetch_failed(server, error_type="invalid_payload")
                return []
            alerts: list[Alert] = []
            for item in payload:
                if not isinstance(item, dict):
                    continue
                try:
                    alerts.append(_to_alert(server, item))
                except ValueError:
                    continue
            return alerts
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            log_fetch_failed(
                server,
                error_type=type(exc).__name__,
                exc_info=logging.getLogger(__name__).isEnabledFor(logging.DEBUG),
            )
            return []
        finally:
            client.close()
