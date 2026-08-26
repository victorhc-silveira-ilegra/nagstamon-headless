from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from domain.entities.alert import Alert
from domain.entities.severity import Severity
from domain.services.alert_view import (
    DISPLAY_TIMEZONE,
    LABEL_WIDTH,
    MISSING,
    NBSP,
    detect_environment,
    format_alarm_start,
    format_clock_time,
    format_duration,
    format_started,
    format_timestamp,
    host_value,
    render_effective_alerts,
    sla_criticality,
    sla_elapsed,
    sla_incident_id,
    started_instant,
    status_information,
)

FETCHED = datetime(2026, 8, 14, 17, 0, 0, tzinfo=UTC)


def _row(label: str, value: str) -> str:
    visible = f"{label}:"
    pad = LABEL_WIDTH - len(visible) + 1
    return f"*{visible}*{NBSP * pad}{value}"


def _alert(**overrides: object) -> Alert:
    payload: dict[str, object] = {
        "server": "core",
        "severity": Severity("critical"),
        "alertname": "DiskFull",
        "app": "db01",
        "desc": "disk is full",
        "status_text": "filesystem /var is 95 percent full",
        "host": "db01.prod",
        "starts_at": FETCHED - timedelta(hours=2, minutes=15),
    }
    payload.update(overrides)
    return Alert(**payload)  # type: ignore[arg-type]


def test_alert_strips_host() -> None:
    assert _alert(host="  db01.prod  ").host == "db01.prod"


def test_host_falls_back_to_app_and_placeholders() -> None:
    assert host_value(_alert(host="", app="web01")) == "web01"
    assert host_value(_alert(host="N/A", app="CGI Service")) == MISSING
    assert host_value(_alert(host="node-a", app="other")) == "node-a"


def test_duration_prefers_string_then_computes() -> None:
    assert (
        format_duration(
            duration_str="0d 3h 0m",
            starts_at=FETCHED - timedelta(minutes=10),
            fetched_at=FETCHED,
        )
        == "0d 3h 0m"
    )
    assert (
        format_duration(
            duration_str="0d  6h 11m 20s",
            starts_at=None,
            fetched_at=FETCHED,
        )
        == "0d 6h 11m 20s"
    )
    assert (
        format_duration(
            duration_str="",
            starts_at=FETCHED - timedelta(days=1, hours=2, minutes=4),
            fetched_at=FETCHED,
        )
        == "1d 2h 4m"
    )
    assert (
        format_duration(duration_str="", starts_at=None, fetched_at=FETCHED) == MISSING
    )
    assert (
        format_duration(
            duration_str="",
            starts_at=FETCHED + timedelta(minutes=1),
            fetched_at=FETCHED,
        )
        == MISSING
    )


def test_started_from_duration_when_clock_missing() -> None:
    assert (
        format_started(
            starts_at=None,
            duration_str="0d 2h 15m",
            fetched_at=FETCHED,
            timezone=DISPLAY_TIMEZONE,
        )
        == "14/08/2026 11:45:00"
    )
    assert (
        format_started(
            starts_at=None,
            duration_str="",
            fetched_at=FETCHED,
            timezone=DISPLAY_TIMEZONE,
        )
        == MISSING
    )


def test_status_information_falls_back_to_desc() -> None:
    assert status_information(_alert(status_text="")) == "disk is full"
    assert status_information(_alert(status_text="N/A", desc="")) == MISSING
    assert status_information(_alert(status_text="'quoted info'")) == "quoted info"
    assert status_information(_alert(status_text='"double quoted"')) == "double quoted"


def test_render_empty_and_singular() -> None:
    empty = render_effective_alerts([], FETCHED, DISPLAY_TIMEZONE)
    assert empty == ""
    one = render_effective_alerts([_alert()], FETCHED, DISPLAY_TIMEZONE)
    assert one.startswith("*#1  CRITICAL*")
    assert "alerta efetivo" not in one


def test_render_card_fields_and_wrap() -> None:
    long_info = "inode " + ("usage high " * 12)
    text = render_effective_alerts(
        [_alert(status_text=long_info, duration_str="", starts_at=None)],
        FETCHED,
        DISPLAY_TIMEZONE,
    )
    assert _row("Status", "CRITICAL") in text
    assert _row("Client", "core") in text
    assert _row("Host", "db01.prod") in text
    assert _row("Service", "DiskFull") in text
    assert _row("Ambiente", "PRD") in text
    assert _row("Duração no Nagstamon", "--") in text
    assert _row("Horário do envio", "14:00:00 (14/08/2026)") in text
    assert _row("Início do alarme", "--") in text
    assert _row("Status information", "inode usage high") in text
    assert _row("Criticidade SLA", "Muito Crítico (Carência: 10m)") in text
    assert _row("Tempo decorrido (SLA)", "--") in text
    assert _row("ID do Incidente (SLA)", "core/DiskFull/db01.prod") in text
    assert f"\n{NBSP * (LABEL_WIDTH + 3)}" in text
    client = next(line for line in text.splitlines() if line.startswith("*Client:*"))
    info = next(
        line for line in text.splitlines() if line.startswith("*Status information:*")
    )
    assert client.index("core") == info.index("inode")


def test_render_started_duration_and_sort() -> None:
    warning = _alert(
        alertname="CPU",
        severity=Severity("warning"),
        starts_at=datetime(2026, 8, 14, 16, 30, 0),
    )
    unknown = _alert(
        alertname="Info",
        severity=Severity("info"),
        host="aaa",
    )
    text = render_effective_alerts(
        [warning, _alert(), unknown],
        FETCHED,
        ZoneInfo("UTC"),
    )
    critical_at = text.index("*#1  CRITICAL*")
    warning_at = text.index("*#2  WARNING*")
    info_at = text.index("*#3  INFO*")
    assert critical_at < warning_at < info_at
    assert _row("Duração no Nagstamon", "0d 2h 15m") in text
    assert _row("Início do alarme", "14:45:00 (14/08/2026)") in text


def test_render_cgi_started_from_duration() -> None:
    text = render_effective_alerts(
        [_alert(starts_at=None, duration_str="0d  2h 15m 3s")],
        FETCHED,
        DISPLAY_TIMEZONE,
    )
    assert _row("Duração no Nagstamon", "0d 2h 15m 3s") in text
    assert _row("Início do alarme", "11:44:57 (14/08/2026)") in text


def test_render_default_timezone_and_placeholders() -> None:
    naive = datetime(2026, 8, 14, 17, 0, 0)
    text = render_effective_alerts(
        [_alert(alertname="NagiosAlert", host="", app="CGI Service", server="svr")],
        naive,
    )
    assert text.startswith("*#1  CRITICAL*")
    assert _row("Host", "--") in text
    assert _row("Service", "--") in text
    assert _row("Ambiente", "--") in text


def test_render_escapes_chat_markup_in_values() -> None:
    text = render_effective_alerts(
        [_alert(status_text="disk *full* _now_")],
        FETCHED,
        DISPLAY_TIMEZONE,
    )
    assert "disk \\*full\\* \\_now\\_" in text


def test_detect_environment_sources() -> None:
    assert detect_environment(_alert(environment="hml")) == "HML"
    assert detect_environment(_alert(environment="prod")) == "PRD"
    assert detect_environment(_alert(server="inbursa-hml-mp", host="h1")) == "HML"
    assert detect_environment(_alert(server="s1", host="server-qa-01")) == "QA"
    assert detect_environment(_alert(server="s1", host="", app="app-dev")) == "DEV"
    assert detect_environment(_alert(server="s1", host="h1", app="a1")) == MISSING


def test_sla_helpers_and_timing() -> None:
    fast = _alert(alertname="DOWN", severity=Severity("critical"), desc="down")
    critical = _alert(
        alertname="HttpError",
        severity=Severity("critical"),
        desc="500 error",
        status_text="500 error",
    )
    low = _alert(
        alertname="Memory",
        severity=Severity("warning"),
        desc="high memory",
        status_text="high memory",
    )
    info = _alert(severity=Severity("info"))
    assert sla_criticality(fast) == "Muito Crítico (Carência: 10m)"
    assert sla_criticality(critical) == "Crítico (Carência: 15m)"
    assert sla_criticality(low) == "Baixo (Carência: 20m)"
    assert sla_criticality(info) == MISSING
    assert sla_incident_id(fast) == "core/DOWN/db01.prod"
    start = FETCHED - timedelta(minutes=10, seconds=15)
    assert (
        sla_elapsed(
            starts_at=start,
            duration_str="",
            fetched_at=FETCHED,
        )
        == "615s (10m 15s)"
    )
    assert (
        sla_elapsed(
            starts_at=None,
            duration_str="",
            fetched_at=FETCHED,
        )
        == MISSING
    )
    assert (
        sla_elapsed(
            starts_at=FETCHED + timedelta(seconds=10),
            duration_str="",
            fetched_at=FETCHED,
        )
        == MISSING
    )
    assert format_clock_time(FETCHED, DISPLAY_TIMEZONE) == "14:00:00 (14/08/2026)"
    assert format_timestamp(FETCHED, DISPLAY_TIMEZONE).endswith("-0300")
    assert (
        format_alarm_start(
            starts_at=None,
            duration_str="",
            fetched_at=FETCHED,
            timezone=DISPLAY_TIMEZONE,
        )
        == MISSING
    )
    assert (
        started_instant(
            starts_at=None,
            duration_str="",
            fetched_at=FETCHED,
        )
        is None
    )
