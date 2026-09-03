from __future__ import annotations

import httpx
import pytest

from domain.entities.monitor_server import MonitorServer
from infrastructure.adapters.http_monitor_probe import HttpMonitorProbeAdapter
from infrastructure.logging.events import MONITOR_PING_FAILED


class _Transport(httpx.BaseTransport):
    def __init__(
        self,
        status_code: int = 200,
        error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = error
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return httpx.Response(self.status_code, text="ok", request=request)


def _am(*, url: str = "http://am.example") -> MonitorServer:
    return MonitorServer(
        name="am",
        url=url,
        proxy="",
        username="user",
        password="secret",
        server_type="alertmanager",
    )


def _nagios() -> MonitorServer:
    return MonitorServer(
        name="core",
        url="http://nagios.example/nagios",
        proxy="",
        username="",
        password="",
        server_type="nagios",
    )


def test_probe_alertmanager_2xx_and_suffix() -> None:
    transport = _Transport(status_code=204)
    probe = HttpMonitorProbeAdapter(timeout_seconds=5.0, transport=transport)
    assert probe.probe(_am()) is True
    assert str(transport.requests[0].url).endswith("/api/v2/alerts")
    transport_ready = _Transport(status_code=200)
    probe_ready = HttpMonitorProbeAdapter(
        timeout_seconds=5.0, transport=transport_ready
    )
    assert probe_ready.probe(_am(url="http://am.example/api/v2/alerts")) is True
    assert str(transport_ready.requests[0].url).endswith("/api/v2/alerts")


def test_probe_nagios_cgi_path() -> None:
    transport = _Transport(status_code=200)
    probe = HttpMonitorProbeAdapter(timeout_seconds=5.0, transport=transport)
    assert probe.probe(_nagios()) is True
    assert "/cgi-bin/status.cgi" in str(transport.requests[0].url)


def test_probe_http_status_and_network(
    caplog: pytest.LogCaptureFixture,
) -> None:
    bad = HttpMonitorProbeAdapter(
        timeout_seconds=5.0, transport=_Transport(status_code=503)
    )
    with caplog.at_level("WARNING"):
        assert bad.probe(_am()) is False
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_PING_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )
    import logging

    logging.getLogger("infrastructure.adapters.http_monitor_probe").setLevel(
        logging.DEBUG
    )
    error = HttpMonitorProbeAdapter(
        timeout_seconds=5.0,
        transport=_Transport(error=httpx.ConnectError("down")),
    )
    assert error.probe(_nagios()) is False


def test_probe_unsupported_zabbix(caplog: pytest.LogCaptureFixture) -> None:
    probe = HttpMonitorProbeAdapter(timeout_seconds=5.0, transport=_Transport())
    server = MonitorServer(
        name="zbx",
        url="http://zabbix.example",
        proxy="",
        username="",
        password="",
        server_type="zabbix",
    )
    with caplog.at_level("WARNING"):
        assert probe.probe(server) is False
    assert any(
        getattr(record, "semantic", {}).get("error_type") == "unsupported"
        for record in caplog.records
        if hasattr(record, "semantic")
    )
