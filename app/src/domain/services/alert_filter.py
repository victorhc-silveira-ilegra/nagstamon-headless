from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime

from domain.entities.alert import Alert

STATUS_INFO_FILTER = re.compile(
    r"(?i)("
    r"Authentication problem|Connection timeout|Service unavailable|"
    r"Unknown error|Monitor URL not valid)"
)
DURATION_FILTER = re.compile(r".*([2-9]|[1-9][0-9]+)d.*|.*0d\s+0h\s+[0-4]m.*")
NOISE_ALERTNAMES = frozenset({"watchdog", "infoinhibitor"})
SKIP_STATES = frozenset({"suppressed", "pending", "unprocessed"})
MIN_DURATION_SECONDS = 300
MAX_DURATION_SECONDS = 172800


class AlertFilterPolicy:
    def is_filtered(self, alert: Alert, now: datetime) -> bool:
        status_text = alert.status_text or f"{alert.alertname} {alert.desc}"
        if STATUS_INFO_FILTER.search(status_text):
            return True
        if alert.duration_str and DURATION_FILTER.search(alert.duration_str):
            return True
        if alert.starts_at is not None:
            start = alert.starts_at
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            current = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
            duration_seconds = (current - start).total_seconds()
            if (
                duration_seconds < MIN_DURATION_SECONDS
                or duration_seconds >= MAX_DURATION_SECONDS
            ):
                return True
        if alert.alertname.lower() in NOISE_ALERTNAMES:
            return True
        if alert.alert_state in SKIP_STATES:
            return True
        return bool(alert.silenced_by or alert.inhibited_by)

    def apply(self, alerts: Sequence[Alert], now: datetime) -> list[Alert]:
        return [alert for alert in alerts if not self.is_filtered(alert, now)]
