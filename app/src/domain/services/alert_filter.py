from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from domain.entities.alert import Alert
from domain.services.alert_hold import (
    HOLD_CRITICAL_SECONDS,
    HOLD_FAST_SECONDS,
    HOLD_WARNING_SECONDS,
    hold_seconds,
)

STATUS_INFO_FILTER = re.compile(
    r"(?i)("
    r"Authentication problem|Connection timeout|Service unavailable|"
    r"Unknown error|Monitor URL not valid)"
)
NOISE_ALERTNAMES = frozenset({"watchdog", "infoinhibitor"})
KUBE_NOISE = re.compile(
    r"(?i)("
    r"kubelet|kubernetes|"
    r"(?<![a-z0-9])k8s(?![a-z0-9])|"
    r"(?<![a-z0-9])kube(?![a-z0-9])"
    r")"
)
SKIP_STATES = frozenset({"suppressed", "pending", "unprocessed"})
MAX_DURATION_SECONDS = 86400
DURATION_UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}
DEFAULT_FILTER_TIMEZONE = ZoneInfo("America/Sao_Paulo")
DEFAULT_WINDOW_START = time(13, 30)
DEFAULT_WINDOW_END = time(18, 0)
DEFAULT_WEEKDAYS = (0, 1, 2, 3, 4)


def parse_duration_seconds(raw: str) -> int | None:
    total = 0
    seen = False
    for token in raw.lower().replace(",", " ").split():
        if len(token) < 2:
            continue
        unit = token[-1]
        amount = token[:-1]
        if unit not in DURATION_UNITS or not amount.isdigit():
            continue
        total += int(amount) * DURATION_UNITS[unit]
        seen = True
    return total if seen else None


def _aware(instant: datetime) -> datetime:
    return instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)


def _is_kubernetes_noise(alert: Alert) -> bool:
    if "pod" in alert.alertname.lower():
        return True
    haystack = f"{alert.alertname} {alert.desc} {alert.status_text}"
    return KUBE_NOISE.search(haystack) is not None


class AlertFilterPolicy:
    def __init__(
        self,
        *,
        window_start: time = DEFAULT_WINDOW_START,
        window_end: time = DEFAULT_WINDOW_END,
        weekdays: Sequence[int] = DEFAULT_WEEKDAYS,
        timezone: ZoneInfo | None = None,
        hold_fast_seconds: int = HOLD_FAST_SECONDS,
        hold_critical_seconds: int = HOLD_CRITICAL_SECONDS,
        hold_warning_seconds: int = HOLD_WARNING_SECONDS,
        max_duration_seconds: int = MAX_DURATION_SECONDS,
        not_before: datetime | None = None,
        window_enabled: bool = True,
    ) -> None:
        self._window_start = window_start
        self._window_end = window_end
        self._weekdays = frozenset(weekdays)
        self._timezone = timezone or DEFAULT_FILTER_TIMEZONE
        self._window_enabled = window_enabled
        self._hold_fast_seconds = hold_fast_seconds
        self._hold_critical_seconds = hold_critical_seconds
        self._hold_warning_seconds = hold_warning_seconds
        self._max_duration_seconds = max_duration_seconds
        self._not_before = not_before

    def _localize(self, instant: datetime) -> datetime:
        return _aware(instant).astimezone(self._timezone)

    def _in_daily_window(self, instant: datetime) -> bool:
        local = self._localize(instant)
        if local.weekday() not in self._weekdays:
            return False
        return self._window_start <= local.time() <= self._window_end

    def _start_instant(self, alert: Alert, now: datetime) -> datetime | None:
        if alert.starts_at is not None:
            return _aware(alert.starts_at)
        parsed = parse_duration_seconds(alert.duration_str)
        if parsed is None:
            return None
        return _aware(now) - timedelta(seconds=parsed)

    def _starts_at_in_window_today(self, start: datetime, now: datetime) -> bool:
        local_start = self._localize(start)
        local_now = self._localize(now)
        if local_start.date() != local_now.date():
            return False
        return self._in_daily_window(start)

    def is_filtered(self, alert: Alert, now: datetime) -> bool:
        if alert.acknowledged:
            return True
        status_text = alert.status_text or f"{alert.alertname} {alert.desc}"
        if STATUS_INFO_FILTER.search(status_text):
            return True
        if alert.alertname.lower() in NOISE_ALERTNAMES:
            return True
        if _is_kubernetes_noise(alert):
            return True
        if alert.alert_state in SKIP_STATES:
            return True
        if alert.silenced_by or alert.inhibited_by:
            return True
        start = self._start_instant(alert, now)
        if start is None:
            return True
        if self._not_before is not None and start < _aware(self._not_before):
            return True
        needed = hold_seconds(
            alert,
            fast=self._hold_fast_seconds,
            critical=self._hold_critical_seconds,
            warning=self._hold_warning_seconds,
        )
        duration_seconds = (_aware(now) - start).total_seconds()
        if needed is None or duration_seconds < needed:
            return True
        if duration_seconds >= self._max_duration_seconds:
            return True
        if not self._window_enabled:
            return False
        if not self._starts_at_in_window_today(start, now):
            return True
        return not self._in_daily_window(now)

    def apply(self, alerts: Sequence[Alert], now: datetime) -> list[Alert]:
        return [alert for alert in alerts if not self.is_filtered(alert, now)]
