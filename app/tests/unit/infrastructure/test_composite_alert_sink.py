from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from domain.entities.alert import Alert
from domain.entities.severity import Severity
from infrastructure.adapters.composite_alert_sink import CompositeAlertSink

NOW = datetime(2026, 8, 14, 17, 0, 0, tzinfo=UTC)


class _FakeSink:
    def __init__(self) -> None:
        self.published: list[Alert] = []
        self.fetched_at: datetime | None = None
        self.calls = 0

    def publish(self, alerts: Sequence[Alert], *, fetched_at: datetime) -> None:
        self.calls += 1
        self.published = list(alerts)
        self.fetched_at = fetched_at


def _alert() -> Alert:
    return Alert(
        server="core",
        severity=Severity("critical"),
        alertname="DiskFull",
        app="db01",
        desc="disk is full",
        starts_at=NOW - timedelta(minutes=30),
    )


def test_composite_publishes_to_all_sinks() -> None:
    first = _FakeSink()
    second = _FakeSink()
    alert = _alert()
    CompositeAlertSink(first, second).publish([alert], fetched_at=NOW)
    assert first.calls == 1
    assert second.calls == 1
    assert first.published == [alert]
    assert second.published == [alert]
    assert first.fetched_at == NOW
    assert second.fetched_at == NOW
