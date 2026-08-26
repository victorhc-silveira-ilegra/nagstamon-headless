from __future__ import annotations

import textwrap
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from domain.entities.alert import Alert
from domain.services.alert_filter import parse_duration_seconds
from domain.services.alert_hold import hold_seconds

DISPLAY_TIMEZONE = ZoneInfo("America/Sao_Paulo")
MISSING = "--"
PLACEHOLDERS = frozenset({"", "n/a", "nagiosalert", "cgi service"})
LABEL_WIDTH = len("Tempo decorrido (SLA):")
INFO_WRAP = 56
NBSP = "\u00a0"
SEVERITY_RANK = {"CRITICAL": 0, "WARNING": 1}

_ENV_NORMALIZE = {
    "PRD": "PRD",
    "PROD": "PRD",
    "PRODUCAO": "PRD",
    "HML": "HML",
    "HOMOLOG": "HML",
    "HOMOLOGACAO": "HML",
    "QA": "QA",
    "DEV": "DEV",
    "DESENV": "DEV",
    "SANDBOX": "SANDBOX",
    "UAT": "UAT",
    "STG": "STG",
    "STAGING": "STG",
}


def _aware(instant: datetime) -> datetime:
    return instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)


def format_timestamp(instant: datetime, timezone: ZoneInfo) -> str:
    return _aware(instant).astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %z")


def format_started_clock(instant: datetime, timezone: ZoneInfo) -> str:
    return _aware(instant).astimezone(timezone).strftime("%d/%m/%Y %H:%M:%S")


def format_clock_time(instant: datetime, timezone: ZoneInfo) -> str:
    return _aware(instant).astimezone(timezone).strftime("%H:%M:%S (%d/%m/%Y)")


def started_instant(
    *,
    starts_at: datetime | None,
    duration_str: str,
    fetched_at: datetime,
) -> datetime | None:
    if starts_at is not None:
        return _aware(starts_at)
    parsed = parse_duration_seconds(duration_str)
    if parsed is None:
        return None
    return _aware(fetched_at) - timedelta(seconds=parsed)


def format_alarm_start(
    *,
    starts_at: datetime | None,
    duration_str: str,
    fetched_at: datetime,
    timezone: ZoneInfo,
) -> str:
    start = started_instant(
        starts_at=starts_at,
        duration_str=duration_str,
        fetched_at=fetched_at,
    )
    if start is None:
        return MISSING
    local = start.astimezone(timezone)
    return local.strftime("%H:%M:%S (%d/%m/%Y)")


def format_started(
    *,
    starts_at: datetime | None,
    duration_str: str,
    fetched_at: datetime,
    timezone: ZoneInfo,
) -> str:
    start = started_instant(
        starts_at=starts_at,
        duration_str=duration_str,
        fetched_at=fetched_at,
    )
    if start is None:
        return MISSING
    return format_started_clock(start, timezone)


def format_duration(
    *,
    duration_str: str,
    starts_at: datetime | None,
    fetched_at: datetime,
) -> str:
    text = " ".join(duration_str.split())
    if text:
        return text
    if starts_at is None:
        return MISSING
    seconds = int((_aware(fetched_at) - _aware(starts_at)).total_seconds())
    if seconds < 0:
        return MISSING
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    return f"{days}d {hours}h {minutes}m"


def detect_environment(alert: Alert) -> str:
    if alert.environment and alert.environment != MISSING:
        normalized = _ENV_NORMALIZE.get(alert.environment.upper())
        return normalized or alert.environment.upper()
    for text in (alert.server, alert.host, alert.app):
        if not text:
            continue
        cleaned = text.replace(".", "-").replace("_", "-").replace("/", "-")
        for part in cleaned.split("-"):
            normalized = _ENV_NORMALIZE.get(part.upper())
            if normalized:
                return normalized
    return MISSING


def sla_criticality(alert: Alert) -> str:
    needed = hold_seconds(alert)
    if needed == 600:
        return "Muito Crítico (Carência: 10m)"
    if needed == 900:
        return "Crítico (Carência: 15m)"
    if needed == 1200:
        return "Baixo (Carência: 20m)"
    return MISSING


def sla_elapsed(
    *,
    starts_at: datetime | None,
    duration_str: str,
    fetched_at: datetime,
) -> str:
    start = started_instant(
        starts_at=starts_at,
        duration_str=duration_str,
        fetched_at=fetched_at,
    )
    if start is None:
        return MISSING
    seconds = int((_aware(fetched_at) - start).total_seconds())
    if seconds < 0:
        return MISSING
    minutes = seconds // 60
    return f"{minutes}m"


def sla_incident_id(alert: Alert) -> str:
    return f"{alert.server}/{alert.alertname}/{host_value(alert)}"


def display_value(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    if text.lower() in PLACEHOLDERS:
        return MISSING
    return text


def host_value(alert: Alert) -> str:
    host = display_value(alert.host)
    if host != MISSING:
        return host
    return display_value(alert.app)


def status_information(alert: Alert) -> str:
    info = display_value(alert.status_text)
    if info != MISSING:
        return info
    return display_value(alert.desc)


def _markup_value(value: str) -> str:
    return (
        value.replace("*", "\\*")
        .replace("_", "\\_")
        .replace("~", "\\~")
        .replace("`", "\\`")
    )


def _labeled(label: str, value: str) -> str:
    visible = f"{label}:"
    prefix = f"*{visible}*"
    gutter = (NBSP * (LABEL_WIDTH - len(visible))) + NBSP
    wrapped = textwrap.wrap(_markup_value(value), width=INFO_WRAP) or [MISSING]
    hang = NBSP * (LABEL_WIDTH + 3)
    first = f"{prefix}{gutter}{wrapped[0]}"
    extra = [f"{hang}{part}" for part in wrapped[1:]]
    return "\n".join([first, *extra])


def _sort_key(alert: Alert) -> tuple[int, str, str, str]:
    rank = SEVERITY_RANK.get(alert.severity.value, 2)
    return (
        rank,
        alert.server.lower(),
        host_value(alert).lower(),
        alert.alertname.lower(),
    )


def render_alert_card(
    alert: Alert,
    fetched_at: datetime,
    timezone: ZoneInfo,
) -> str:
    duration = format_duration(
        duration_str=alert.duration_str,
        starts_at=alert.starts_at,
        fetched_at=fetched_at,
    )
    sent_clock = format_clock_time(fetched_at, timezone)
    alarm_start = format_alarm_start(
        starts_at=alert.starts_at,
        duration_str=alert.duration_str,
        fetched_at=fetched_at,
        timezone=timezone,
    )
    return "\n".join(
        [
            _labeled("Status", alert.severity.value),
            _labeled("Client", display_value(alert.server)),
            _labeled("Host", host_value(alert)),
            _labeled("Service", display_value(alert.alertname)),
            _labeled("Ambiente", detect_environment(alert)),
            _labeled("Duração no Nagstamon", duration),
            _labeled("Horário do envio", sent_clock),
            _labeled("Início do alarme", alarm_start),
            _labeled("Status information", status_information(alert)),
            _labeled("Criticidade SLA", sla_criticality(alert)),
            _labeled(
                "Tempo decorrido (SLA)",
                sla_elapsed(
                    starts_at=alert.starts_at,
                    duration_str=alert.duration_str,
                    fetched_at=fetched_at,
                ),
            ),
            _labeled("ID do Incidente (SLA)", sla_incident_id(alert)),
        ]
    )


def render_effective_alerts(
    alerts: Sequence[Alert],
    fetched_at: datetime,
    timezone: ZoneInfo | None = None,
) -> str:
    if not alerts:
        return ""
    zone = timezone or DISPLAY_TIMEZONE
    cards = [
        render_alert_card(alert, fetched_at, zone)
        for alert in sorted(alerts, key=_sort_key)
    ]
    return "\n\n".join(cards)
