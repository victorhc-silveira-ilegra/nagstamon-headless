from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from domain.entities.monitor_server import MonitorServer
from infrastructure.adapters.alertmanager_http import AlertmanagerHttpClient
from infrastructure.adapters.http_client import build_http_client
from infrastructure.adapters.nagios_cgi_http import NagiosCgiHttpClient
from infrastructure.logging.events import MONITOR_FETCH_FAILED

NAGIOS_HTML = """
<table>
<tr><td class='statusCRITICAL'><b>disk full on /</b></td></tr>
<tr><td class='statusWARNING'>swap low</td></tr>
</table>
"""


class _Transport(httpx.BaseTransport):
    def __init__(
        self,
        status_code: int = 200,
        body: str = "[]",
        content_type: str = "application/json",
        error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.content_type = content_type
        self.error = error
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return httpx.Response(
            self.status_code,
            text=self.body,
            headers={"content-type": self.content_type},
            request=request,
        )


def _am_server(*, url: str = "http://am.example") -> MonitorServer:
    return MonitorServer(
        name="am",
        url=url,
        proxy="",
        username="user",
        password="secret",
        server_type="alertmanager",
    )


def _nagios_server() -> MonitorServer:
    return MonitorServer(
        name="core",
        url="http://nagios.example/nagios",
        proxy="",
        username="",
        password="",
        server_type="nagios",
    )


def test_build_http_client_with_and_without_auth() -> None:
    with_auth = build_http_client(_am_server(), 5.0)
    assert with_auth is not None
    with_auth.close()
    proxied = MonitorServer(
        name="am",
        url="http://am.example",
        proxy="http://proxy.example:3128",
        username="",
        password="",
        server_type="alertmanager",
    )
    client = build_http_client(proxied, 5.0)
    client.close()
    anonymous = build_http_client(_nagios_server(), 5.0)
    anonymous.close()


def test_alertmanager_parses_payload() -> None:
    payload: list[dict[str, Any]] = [
        "skip",
        {
            "labels": {
                "alertname": "DiskFull",
                "severity": "critical",
                "application": "db01",
                "environment": "prd",
            },
            "annotations": {"title": "disk is full"},
            "startsAt": "2026-08-13T10:00:00Z",
            "status": {"state": "active", "silencedBy": ["s1"], "inhibitedBy": "i1"},
        },
        {
            "labels": {"alertname": "CPU", "instance": "web01"},
            "annotations": {"message": "high cpu"},
            "startsAt": "not-a-date",
            "status": {},
        },
        {
            "labels": "bad",
            "annotations": None,
            "status": 1,
        },
    ]
    transport = _Transport(body=json.dumps(payload))
    client = AlertmanagerHttpClient(timeout_seconds=5.0, transport=transport)
    alerts = client.fetch(_am_server(url="http://am.example/api/v2/alerts"))
    assert transport.requests[0].url.path.endswith("/api/v2/alerts")
    assert len(alerts) == 3
    assert alerts[0].alertname == "DiskFull"
    assert alerts[0].app == "db01"
    assert alerts[0].host == "db01"
    assert alerts[0].environment == "PRD"
    assert alerts[0].status_text == "disk is full"
    assert alerts[0].severity.value == "CRITICAL"
    assert alerts[0].silenced_by == ("s1",)
    assert alerts[0].inhibited_by == ("i1",)
    assert alerts[0].starts_at is not None
    assert alerts[1].app == "web01"
    assert alerts[1].host == "web01"
    assert alerts[1].status_text == "high cpu"
    assert alerts[1].starts_at is None
    assert alerts[2].alertname == "N/A"
    assert alerts[2].desc == "Sem descricao"
    assert alerts[2].host == "N/A"


def test_alertmanager_appends_api_path() -> None:
    transport = _Transport(body="[]")
    client = AlertmanagerHttpClient(timeout_seconds=5.0, transport=transport)
    client.fetch(_am_server(url="http://am.example/"))
    assert str(transport.requests[0].url) == "http://am.example/api/v2/alerts"


def test_alertmanager_http_error_status(caplog: pytest.LogCaptureFixture) -> None:
    transport = _Transport(status_code=500, body="boom")
    client = AlertmanagerHttpClient(timeout_seconds=5.0, transport=transport)
    with caplog.at_level("WARNING"):
        assert client.fetch(_am_server()) == []
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_FETCH_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_alertmanager_invalid_payload(caplog: pytest.LogCaptureFixture) -> None:
    transport = _Transport(body='{"not":"list"}')
    client = AlertmanagerHttpClient(timeout_seconds=5.0, transport=transport)
    with caplog.at_level("WARNING"):
        assert client.fetch(_am_server()) == []


def test_alertmanager_invalid_json(caplog: pytest.LogCaptureFixture) -> None:
    transport = _Transport(body="not-json", content_type="application/json")
    client = AlertmanagerHttpClient(timeout_seconds=5.0, transport=transport)
    with caplog.at_level("WARNING"):
        assert client.fetch(_am_server()) == []


def test_alertmanager_transport_error(caplog: pytest.LogCaptureFixture) -> None:
    request = httpx.Request("GET", "http://am.example/api/v2/alerts")
    transport = _Transport(error=httpx.ConnectError("refused", request=request))
    client = AlertmanagerHttpClient(timeout_seconds=5.0, transport=transport)
    with caplog.at_level("WARNING"):
        assert client.fetch(_am_server()) == []


def test_alertmanager_debug_exc_info(caplog: pytest.LogCaptureFixture) -> None:
    import logging as logging_mod

    logging_mod.getLogger("infrastructure.adapters.alertmanager_http").setLevel(
        logging_mod.DEBUG
    )
    transport = _Transport(status_code=503, body="no")
    client = AlertmanagerHttpClient(timeout_seconds=5.0, transport=transport)
    with caplog.at_level("DEBUG"):
        assert client.fetch(_am_server()) == []


def test_alertmanager_skips_invalid_item() -> None:
    payload = [{"labels": {"severity": "   "}, "annotations": {}, "status": {}}]
    transport = _Transport(body=json.dumps(payload))
    client = AlertmanagerHttpClient(timeout_seconds=5.0, transport=transport)
    assert client.fetch(_am_server()) == []


def test_alertmanager_maps_host_and_description() -> None:
    payload = [
        {
            "labels": {
                "alertname": "NodeDown",
                "hostname": "node-a",
                "instance": "ignored:9100",
            },
            "annotations": {
                "description": "node unreachable for 10m",
                "title": "Node down",
            },
            "status": {},
        },
        {
            "labels": {"alertname": "Ping", "host": "edge-1"},
            "annotations": {"summary": "ping failed"},
            "status": {},
        },
        {
            "labels": {"alertname": "OnlyDesc"},
            "annotations": {"description": "only desc"},
            "status": {},
        },
        {
            "labels": {
                "alertname": "KubePodNotReady",
                "pod": "spi-standin-stub-1",
                "namespace": "mip-hml",
            },
            "annotations": {"description": "pod not ready"},
            "status": {},
        },
        {
            "labels": {"alertname": "ERROR-500", "namespace": "mip-prd"},
            "annotations": {"description": "http 500"},
            "status": {},
        },
    ]
    transport = _Transport(body=json.dumps(payload))
    client = AlertmanagerHttpClient(timeout_seconds=5.0, transport=transport)
    alerts = client.fetch(_am_server())
    assert alerts[0].host == "node-a"
    assert alerts[0].desc == "Node down"
    assert alerts[0].status_text == "node unreachable for 10m"
    assert alerts[1].host == "edge-1"
    assert alerts[1].status_text == "ping failed"
    assert alerts[2].desc == "only desc"
    assert alerts[2].status_text == "only desc"
    assert alerts[3].host == "spi-standin-stub-1"
    assert alerts[4].host == "mip-prd"


def test_nagios_parses_html() -> None:
    transport = _Transport(body=NAGIOS_HTML, content_type="text/html")
    client = NagiosCgiHttpClient(timeout_seconds=5.0, transport=transport)
    alerts = client.fetch(_nagios_server())
    assert len(alerts) == 2
    assert alerts[0].severity.value == "CRITICAL"
    assert "disk full" in alerts[0].desc
    assert alerts[1].severity.value == "WARNING"
    assert alerts[0].alertname == "NagiosAlert"
    assert alerts[0].host == ""
    assert alerts[0].acknowledged is False
    assert "status.cgi" in str(transport.requests[0].url)


def test_nagios_parses_host_service_duration() -> None:
    html = """
    <table>
    <tr><td class='statusOK'>healthy</td></tr>
    <tr>
      <td><a href='extinfo.cgi?type=1&host=db%2D01'>db-01</a></td>
      <td class='statusCRITICAL'>
        <a href='extinfo.cgi?type=2&host=db-01&service=Disk+/var'>Disk /var</a>
      </td>
      <td>0d 2h 15m 3s</td>
      <td>DISK CRITICAL ACKNOWLEDGED - free space 5%</td>
    </tr>
    <tr><td class='statusWARNING'>swap low</td></tr>
    <tr><td class='statusCRITICAL'></td></tr>
    </table>
    """
    transport = _Transport(body=html, content_type="text/html")
    client = NagiosCgiHttpClient(timeout_seconds=5.0, transport=transport)
    alerts = client.fetch(_nagios_server())
    assert len(alerts) == 3
    assert alerts[0].host == "db-01"
    assert alerts[0].app == "db-01"
    assert alerts[0].alertname == "Disk /var"
    assert alerts[0].duration_str == "0d 2h 15m 3s"
    assert alerts[0].acknowledged is True
    assert "free space 5%" in alerts[0].status_text
    assert alerts[1].severity.value == "WARNING"
    assert alerts[1].status_text == "swap low"
    assert alerts[2].alertname == "NagiosAlert"
    assert alerts[2].desc == "NagiosAlert"


def test_nagios_parses_nested_status_table() -> None:
    html = """
    <table>
    <tr>
      <td></td>
      <td class='statusBGCRITICAL'>
        <table><tr><td>
          <a href='extinfo.cgi?type=2&host=web01&service=HTTP'>HTTP</a>
        </td></tr></table>
      </td>
      <td class='statusCRITICAL'>CRITICAL</td>
      <td class='statusBGCRITICAL' nowrap>08-14-2026 14:48:34</td>
      <td class='statusBGCRITICAL' nowrap>0d  2h 15m 3s</td>
      <td class='statusBGCRITICAL'>3/3</td>
      <td class='statusBGCRITICAL'>connection refused</td>
    </tr>
    <tr>
      <td></td>
      <td class='statusBGCRITICALACK'>
        <a href='extinfo.cgi?type=2&host=web01&service=CPU'>CPU</a>
        <img alt='This service problem has been acknowledged'>
      </td>
      <td class='statusCRITICALACK'>CRITICAL</td>
      <td class='statusBGCRITICALACK'>08-14-2026 14:48:34</td>
      <td class='statusBGCRITICALACK'>0d  3h 0m 0s</td>
      <td class='statusBGCRITICALACK'>3/3</td>
      <td class='statusBGCRITICALACK'>load high</td>
    </tr>
    </table>
    """
    transport = _Transport(body=html, content_type="text/html")
    client = NagiosCgiHttpClient(timeout_seconds=5.0, transport=transport)
    alerts = client.fetch(_nagios_server())
    assert len(alerts) == 2
    assert alerts[0].host == "web01"
    assert alerts[0].alertname == "HTTP"
    assert alerts[0].duration_str == "0d  2h 15m 3s"
    assert alerts[0].acknowledged is False
    assert alerts[0].status_text == "connection refused"
    assert alerts[1].alertname == "CPU"
    assert alerts[1].host == "web01"
    assert alerts[1].acknowledged is True


def test_nagios_html_cells_without_href_and_stray_tags() -> None:
    html = """
    <a href=''></a><img><tr></tr></td></tr>
    <tr><td class='statusOK'>skip</tr></td>
    <table>
    <tr>
      <td>box01</td>
      <td>Swap</td>
      <td class='statusWARNING'>WARNING</td>
      <td>last</td>
      <td>not-duration</td>
      <td>1/1</td>
      <td>0d 0h 12m 0s low</td>
    </tr>
    <tr><td class='statusCRITICAL'><a href=''>x</a><img src='ack.gif'>y</td></tr>
    </table>
    """
    transport = _Transport(body=html, content_type="text/html")
    client = NagiosCgiHttpClient(timeout_seconds=5.0, transport=transport)
    alerts = client.fetch(_nagios_server())
    assert len(alerts) == 2
    assert alerts[0].host == "box01"
    assert alerts[0].alertname == "Swap"
    assert alerts[0].duration_str == "0d 0h 12m 0s"
    assert alerts[1].alertname == "NagiosAlert"
    assert alerts[1].host == "box01"


def test_nagios_marks_acknowledged() -> None:
    html = """
    <table>
    <tr><td class='statusCRITICAL'>disk full ACKNOWLEDGED</td></tr>
    </table>
    """
    transport = _Transport(body=html, content_type="text/html")
    client = NagiosCgiHttpClient(timeout_seconds=5.0, transport=transport)
    alerts = client.fetch(_nagios_server())
    assert len(alerts) == 1
    assert alerts[0].acknowledged is True


def test_nagios_http_error_status(caplog: pytest.LogCaptureFixture) -> None:
    transport = _Transport(status_code=404, body="missing", content_type="text/html")
    client = NagiosCgiHttpClient(timeout_seconds=5.0, transport=transport)
    with caplog.at_level("WARNING"):
        assert client.fetch(_nagios_server()) == []


def test_nagios_transport_error(caplog: pytest.LogCaptureFixture) -> None:
    request = httpx.Request("GET", "http://nagios.example/nagios")
    transport = _Transport(error=httpx.ConnectError("refused", request=request))
    client = NagiosCgiHttpClient(timeout_seconds=5.0, transport=transport)
    with caplog.at_level("WARNING"):
        assert client.fetch(_nagios_server()) == []


def test_nagios_debug_exc_info() -> None:
    import logging as logging_mod

    logging_mod.getLogger("infrastructure.adapters.nagios_cgi_http").setLevel(
        logging_mod.DEBUG
    )
    transport = _Transport(status_code=500, body="err", content_type="text/html")
    client = NagiosCgiHttpClient(timeout_seconds=5.0, transport=transport)
    assert client.fetch(_nagios_server()) == []
