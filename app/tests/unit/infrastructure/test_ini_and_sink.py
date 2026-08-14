from __future__ import annotations

import base64
import zlib
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest

from domain.entities.alert import Alert
from domain.entities.severity import Severity
from infrastructure.adapters.ini_server_config import IniServerConfigAdapter
from infrastructure.adapters.stdout_alert_sink import StdoutAlertSink
from infrastructure.adapters.system_clock import SystemClock
from infrastructure.logging.events import MONITOR_CONFIG_FAILED, POLL_SINK_PUBLISHED


def test_system_clock_returns_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == UTC.utcoffset(now)


def test_ini_missing_directory(tmp_path: Path) -> None:
    adapter = IniServerConfigAdapter(tmp_path / "missing", default_proxy="http://p")
    assert adapter.list_enabled() == []


def test_ini_reads_enabled_servers(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")
    (tmp_path / "server_am.conf").write_text(
        "[Server]\n"
        "enabled=True\n"
        "monitor_url=http://am.example\n"
        "type=alertmanager\n"
        "username=user\n"
        "password=secret\n",
        encoding="utf-8",
    )
    (tmp_path / "core.conf").write_text(
        "[Disabled]\n"
        "enabled=False\n"
        "url=http://skip.example\n"
        "[Empty]\n"
        "enabled=True\n"
        "url=\n"
        "[Nagios]\n"
        "enabled=True\n"
        "url=http://nagios.example\n"
        "proxy_address=http://custom:3128\n"
        "type=nagios\n",
        encoding="utf-8",
    )
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="http://default:3128")
    servers = adapter.list_enabled()
    by_name = {item.name: item for item in servers}
    assert by_name["am"].url == "http://am.example"
    assert by_name["am"].proxy == "http://default:3128"
    assert by_name["am"].username == "user"
    assert by_name["am"].password == "secret"
    assert by_name["am"].is_alertmanager is True
    assert by_name["core"].url == "http://nagios.example"
    assert by_name["core"].proxy == "http://custom:3128"
    assert len(servers) == 2


def test_ini_deobfuscates_nagstamon_secrets(tmp_path: Path) -> None:
    def _obfuscate(plain: str) -> str:
        blob = plain.encode()
        for _ in range(5):
            encoded = base64.b64encode(blob).decode()
            blob = zlib.compress(encoded[::-1].encode())
        return base64.b64encode(blob).decode()

    user = _obfuscate("cgi-user")
    password = _obfuscate("cgi-secret")
    (tmp_path / "server_core.conf").write_text(
        "[Server]\n"
        "enabled=True\n"
        "monitor_url=http://nagios.example\n"
        "type=Nagios\n"
        f"username={user}\n"
        f"password={password}\n",
        encoding="utf-8",
    )
    servers = IniServerConfigAdapter(tmp_path, default_proxy="").list_enabled()
    assert len(servers) == 1
    assert servers[0].username == "cgi-user"
    assert servers[0].password == "cgi-secret"


def test_ini_skips_invalid_section(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "bad.conf").write_text(
        "[Server]\nenabled=maybe\nurl=http://x\n",
        encoding="utf-8",
    )
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="")
    with caplog.at_level("WARNING"):
        assert adapter.list_enabled() == []
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_CONFIG_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_ini_skips_undecodable_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "broken.conf").write_bytes(b"\xff\xfe")
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="")
    with caplog.at_level("WARNING"):
        assert adapter.list_enabled() == []
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_CONFIG_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_ini_empty_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "ghost.conf"
    path.write_text("[Server]\nenabled=True\nurl=http://x\n", encoding="utf-8")
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="")

    def _empty_read(self: object, *args: object, **kwargs: object) -> list[str]:
        return []

    monkeypatch.setattr(
        "infrastructure.adapters.ini_server_config.configparser.ConfigParser.read",
        _empty_read,
    )
    with caplog.at_level("WARNING"):
        assert adapter.list_enabled() == []
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_CONFIG_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_stdout_sink_prints_alerts(caplog: pytest.LogCaptureFixture) -> None:
    stream = StringIO()
    sink = StdoutAlertSink(stream=stream)
    alert = Alert(
        server="core-very-long-server-name-exceeds-limit",
        severity=Severity("critical"),
        alertname="DiskFull",
        app="db01",
        desc="disk is full",
        status_text="filesystem /var is 95 percent full",
        host="db01.prod",
        duration_str="0d 2h 15m",
        starts_at=datetime(2026, 8, 13, 10, 0, 0, tzinfo=UTC),
    )
    fetched_at = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)
    with caplog.at_level("INFO"):
        sink.publish([alert], fetched_at=fetched_at)
    text = stream.getvalue()
    assert "1 alerta efetivo" in text
    assert "*Client:*" in text
    assert "core-very-long-server-name-exceeds-limit" in text
    assert "*Host:*" in text
    assert "db01.prod" in text
    assert "*Service:*" in text
    assert "DiskFull" in text
    assert "*Status:*" in text
    assert "CRITICAL" in text
    assert "*Duration:*" in text
    assert "0d 2h 15m" in text
    assert "*Started:*" in text
    assert "13/08/2026 07:00:00" in text
    assert "*Status information:*" in text
    assert "filesystem /var is 95 percent full" in text
    assert any(
        getattr(record, "semantic", {}).get("event") == POLL_SINK_PUBLISHED
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_stdout_sink_default_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = StringIO()
    monkeypatch.setattr(
        "infrastructure.adapters.stdout_alert_sink.sys.stdout",
        captured,
    )
    StdoutAlertSink().publish(
        [],
        fetched_at=datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC),
    )
    assert "0 alertas efetivos" in captured.getvalue()
