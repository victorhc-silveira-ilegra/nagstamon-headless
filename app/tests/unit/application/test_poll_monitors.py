from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from application.use_cases.poll_monitors import (
    PollMonitorsUseCase,
    fingerprint_for,
)
from domain.entities.alert import Alert
from domain.entities.monitor_server import MonitorServer
from domain.entities.severity import Severity

NOW = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, current: datetime | None = None) -> None:
        self.current = current or NOW

    def now(self) -> datetime:
        return self.current


class FakeServerConfig:
    def __init__(self, servers: Sequence[MonitorServer]) -> None:
        self._servers = list(servers)

    def list_enabled(self) -> Sequence[MonitorServer]:
        return list(self._servers)


class FakeMonitorClient:
    def __init__(self, alerts: Sequence[Alert] | None = None) -> None:
        self._alerts = list(alerts or [])
        self.seen_servers: list[MonitorServer] = []

    def fetch_all(self, servers: Sequence[MonitorServer]) -> Sequence[Alert]:
        self.seen_servers = list(servers)
        return list(self._alerts)


class FakeAlertSink:
    def __init__(self, error: Exception | None = None) -> None:
        self.published: list[Alert] = []
        self.fetched_at: datetime | None = None
        self.error = error
        self.calls = 0

    def publish(self, alerts: Sequence[Alert], *, fetched_at: datetime) -> None:
        self.calls += 1
        if self.error is not None:
            raise self.error
        self.published = list(alerts)
        self.fetched_at = fetched_at


class FakeLedger:
    def __init__(self) -> None:
        self.claims: dict[str, datetime] = {}
        self.released: list[str] = []

    def try_claim(
        self, *, fingerprint: str, now: datetime, window_minutes: int
    ) -> bool:
        cutoff = now - timedelta(minutes=window_minutes)
        claimed_at = self.claims.get(fingerprint)
        if claimed_at is not None and claimed_at > cutoff:
            return False
        self.claims[fingerprint] = now
        return True

    def release(self, *, fingerprint: str) -> None:
        self.released.append(fingerprint)
        self.claims.pop(fingerprint, None)


def _server(name: str = "core") -> MonitorServer:
    return MonitorServer(
        name=name,
        url="http://monitor.example",
        proxy="",
        username="",
        password="",
        server_type="nagios",
    )


def _alert(*, alertname: str = "DiskFull", **overrides: object) -> Alert:
    payload: dict[str, object] = {
        "server": "core",
        "severity": Severity("critical"),
        "alertname": alertname,
        "app": "db01",
        "desc": "disk is full",
        "starts_at": NOW - timedelta(hours=1),
    }
    payload.update(overrides)
    return Alert(**payload)  # type: ignore[arg-type]


def _use_case(
    *,
    alerts: Sequence[Alert],
    sink: FakeAlertSink,
    ledger: FakeLedger | None = None,
    clock: FakeClock | None = None,
    window: int = 30,
) -> PollMonitorsUseCase:
    return PollMonitorsUseCase(
        server_config=FakeServerConfig([_server()]),
        monitor_client=FakeMonitorClient(alerts),
        alert_sink=sink,
        clock=clock or FakeClock(),
        dispatch_ledger=ledger,
        dedup_window_minutes=window,
    )


def test_use_case_empty_servers() -> None:
    sink = FakeAlertSink()
    result = PollMonitorsUseCase(
        server_config=FakeServerConfig([]),
        monitor_client=FakeMonitorClient([_alert()]),
        alert_sink=sink,
        clock=FakeClock(),
    ).execute()
    assert result.servers_count == 0
    assert result.alerts_count == 1
    assert result.claimed_count == 1
    assert sink.fetched_at == NOW


def test_use_case_filters_noise_and_publishes_effective() -> None:
    keep = _alert(alertname="DiskFull")
    noise = _alert(alertname="Watchdog")
    sink = FakeAlertSink()
    client = FakeMonitorClient([keep, noise])
    servers = [_server()]
    result = PollMonitorsUseCase(
        server_config=FakeServerConfig(servers),
        monitor_client=client,
        alert_sink=sink,
        clock=FakeClock(),
    ).execute()
    assert client.seen_servers == servers
    assert result.servers_count == 1
    assert result.alerts_count == 1
    assert sink.published == [keep]


def test_use_case_fail_open_empty_fetch() -> None:
    sink = FakeAlertSink()
    result = PollMonitorsUseCase(
        server_config=FakeServerConfig([_server()]),
        monitor_client=FakeMonitorClient([]),
        alert_sink=sink,
        clock=FakeClock(),
    ).execute()
    assert result.alerts_count == 0
    assert sink.published == []
    assert sink.calls == 1


def test_fingerprint_is_sha256_of_dedup_key() -> None:
    alert = _alert()
    expected = hashlib.sha256(alert.dedup_key().encode()).hexdigest()
    assert fingerprint_for(alert) == expected


def test_ledger_claims_first_and_skips_second() -> None:
    alert = _alert()
    ledger = FakeLedger()
    sink = FakeAlertSink()
    first = _use_case(alerts=[alert], sink=sink, ledger=ledger).execute()
    assert first.claimed_count == 1
    assert sink.published == [alert]
    sink2 = FakeAlertSink()
    second = _use_case(alerts=[alert], sink=sink2, ledger=ledger).execute()
    assert second.claimed_count == 0
    assert second.skipped_duplicate_count == 1
    assert sink2.calls == 0


def test_ledger_reclaims_after_window() -> None:
    alert = _alert()
    ledger = FakeLedger()
    clock = FakeClock()
    _use_case(
        alerts=[alert], sink=FakeAlertSink(), ledger=ledger, clock=clock
    ).execute()
    clock.current = NOW + timedelta(minutes=30)
    sink = FakeAlertSink()
    result = _use_case(alerts=[alert], sink=sink, ledger=ledger, clock=clock).execute()
    assert result.claimed_count == 1
    assert sink.published == [alert]


def test_sink_failure_releases_claim() -> None:
    alert = _alert()
    ledger = FakeLedger()
    boom = FakeAlertSink(error=RuntimeError("sink"))
    with pytest.raises(RuntimeError, match="sink"):
        _use_case(alerts=[alert], sink=boom, ledger=ledger).execute()
    assert ledger.released == [fingerprint_for(alert)]
    sink = FakeAlertSink()
    result = _use_case(alerts=[alert], sink=sink, ledger=ledger).execute()
    assert result.claimed_count == 1
    assert sink.published == [alert]


def test_intra_cycle_duplicates_claim_once() -> None:
    first = _alert()
    twin = _alert()
    ledger = FakeLedger()
    sink = FakeAlertSink()
    result = _use_case(alerts=[first, twin], sink=sink, ledger=ledger).execute()
    assert result.claimed_count == 1
    assert result.skipped_duplicate_count == 1
    assert sink.published == [first]


def test_dedup_off_publishes_all_effective() -> None:
    keep = _alert()
    twin = _alert()
    sink = FakeAlertSink()
    result = _use_case(alerts=[keep, twin], sink=sink, ledger=None).execute()
    assert result.claimed_count == 2
    assert result.skipped_duplicate_count == 0
    assert sink.published == [keep, twin]
