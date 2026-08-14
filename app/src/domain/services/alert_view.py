from __future__ import annotations

import textwrap
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from domain.entities.alert import Alert
from domain.services.alert_filter import parse_duration_seconds

DISPLAY_TIMEZONE = ZoneInfo("America/Sao_Paulo")
MISSING = "--"
PLACEHOLDERS = frozenset({"", "n/a", "nagiosalert", "cgi service"})
LABEL_WIDTH = len("Status information:")
INFO_WRAP = 56
NBSP = "\u00a0"
SEVERITY_RANK = {"CRITICAL": 0, "WARNING": 1}


def _aware(instant: datetime) -> datetime:
    return instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)


def format_timestamp(instant: datetime, timezone: ZoneInfo) -> str:
    return _aware(instant).astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %z")


def format_started_clock(instant: datetime, timezone: ZoneInfo) -> str:
    return _aware(instant).astimezone(timezone).strftime("%d/%m/%Y %H:%M:%S")


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


def format_started(
    *,
    starts_at: datetime | None,
    duration_str: str,
    fetched_at: datetime,
    timezone: ZoneInfo,
) -> str:
    if starts_at is not None:
        return format_started_clock(starts_at, timezone)
    parsed = parse_duration_seconds(duration_str)
    if parsed is None:
        return MISSING
    started_at = _aware(fetched_at) - timedelta(seconds=parsed)
    return format_started_clock(started_at, timezone)


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
    index: int,
) -> str:
    started = format_started(
        starts_at=alert.starts_at,
        duration_str=alert.duration_str,
        fetched_at=fetched_at,
        timezone=timezone,
    )
    duration = format_duration(
        duration_str=alert.duration_str,
        starts_at=alert.starts_at,
        fetched_at=fetched_at,
    )
    return "\n".join(
        [
            f"*#{index}  {alert.severity.value}*",
            _labeled("Client", display_value(alert.server)),
            _labeled("Host", host_value(alert)),
            _labeled("Service", display_value(alert.alertname)),
            _labeled("Status", alert.severity.value),
            _labeled("Duration", duration),
            _labeled("Started", started),
            _labeled("Status information", status_information(alert)),
        ]
    )


def render_effective_alerts(
    alerts: Sequence[Alert],
    fetched_at: datetime,
    timezone: ZoneInfo | None = None,
) -> str:
    zone = timezone or DISPLAY_TIMEZONE
    count = len(alerts)
    noun = "alerta efetivo" if count == 1 else "alertas efetivos"
    stamp = format_timestamp(fetched_at, zone)
    header = f"*[{stamp}]*  *{count} {noun}*"
    if count == 0:
        return header
    cards = [
        render_alert_card(alert, fetched_at, zone, index)
        for index, alert in enumerate(sorted(alerts, key=_sort_key), start=1)
    ]
    return header + "\n\n" + "\n\n".join(cards)
