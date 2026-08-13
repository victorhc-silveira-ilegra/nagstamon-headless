from __future__ import annotations

import logging
from collections.abc import Sequence

import pytest

from domain.entities.alert import Alert
from domain.entities.monitor_server import MonitorServer
from domain.entities.severity import Severity
from infrastructure.adapters.composite_monitor_client import CompositeMonitorClient
from infrastructure.logging.events import MONITOR_FETCH_FAILED


def _server(name: str, server_type: str) -> MonitorServer:
    return MonitorServer(
        name=name,
        url=f"http://{name}.example",
        proxy="",
        username="",
        password="",
        server_type=server_type,
    )


class FakeClient:
    def __init__(
        self,
        alerts: Sequence[Alert] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.alerts = list(alerts or [])
        self.error = error
        self.seen: list[MonitorServer] = []

    def fetch(self, server: MonitorServer) -> list[Alert]:
        self.seen.append(server)
        if self.error is not None:
            raise self.error
        return list(self.alerts)


def _alert(server: str, name: str) -> Alert:
    return Alert(
        server=server,
        severity=Severity("warning"),
        alertname=name,
        app="app",
        desc="d",
    )


def test_composite_empty_servers() -> None:
    client = CompositeMonitorClient(
        alertmanager=FakeClient(),  # type: ignore[arg-type]
        nagios=FakeClient(),  # type: ignore[arg-type]
        max_workers=0,
    )
    assert client.fetch_all([]) == []


def test_composite_routes_and_collects() -> None:
    am_alert = _alert("am", "AM")
    nag_alert = _alert("core", "NAG")
    am = FakeClient([am_alert])
    nagios = FakeClient([nag_alert])
    client = CompositeMonitorClient(
        alertmanager=am,  # type: ignore[arg-type]
        nagios=nagios,  # type: ignore[arg-type]
        max_workers=4,
    )
    result = client.fetch_all(
        [_server("am", "alertmanager"), _server("core", "nagios")]
    )
    assert result == [am_alert, nag_alert]
    assert am.seen[0].name == "am"
    assert nagios.seen[0].name == "core"


def test_composite_fail_open_on_unexpected_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    am = FakeClient(error=RuntimeError("boom"))
    client = CompositeMonitorClient(
        alertmanager=am,  # type: ignore[arg-type]
        nagios=FakeClient(),  # type: ignore[arg-type]
    )
    with caplog.at_level("WARNING"):
        result = client.fetch_all([_server("am", "alertmanager")])
    assert result == []
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_FETCH_FAILED
        and record.levelno == logging.WARNING
        for record in caplog.records
        if hasattr(record, "semantic")
    )
