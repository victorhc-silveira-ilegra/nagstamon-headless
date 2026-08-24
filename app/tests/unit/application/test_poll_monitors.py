from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from application.use_cases.poll_monitors import (
    PollMonitorsUseCase,
    fingerprint_for,
)
from domain.entities.alert import Alert
from domain.entities.monitor_server import MonitorServer
from domain.entities.severity import Severity

NOW = datetime(2026, 8, 13, 17, 0, 0, tzinfo=UTC)


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
    def __init__(
        self,
        error: Exception | None = None,
        fail_on: int | None = None,
    ) -> None:
        self.published: list[Alert] = []
        self.fetched_at: datetime | None = None
        self.error = error
        self.calls = 0
        self.fail_on: int | None = fail_on

    def publish(self, alerts: Sequence[Alert], *, fetched_at: datetime) -> None:
        self.calls += 1
        if self.error is not None and (
            self.fail_on is None or self.calls == self.fail_on
        ):
            raise self.error
        self.published.extend(list(alerts))
        self.fetched_at = fetched_at


class FakeLedger:
    def __init__(self) -> None:
        self.claims: dict[str, datetime] = {}
        self.released: list[str] = []
        self.confirmed: list[str] = []

    def try_claim(
        self, *, fingerprint: str, now: datetime, window_minutes: int
    ) -> bool:
        _ = window_minutes
        claimed_at = self.claims.get(fingerprint)
        if claimed_at is not None:
            return False
        self.claims[fingerprint] = now
        return True

    def confirm(self, *, fingerprint: str, now: datetime) -> None:
        self.confirmed.append(fingerprint)
        self.claims[fingerprint] = now

    def release(self, *, fingerprint: str) -> None:
        self.released.append(fingerprint)
        self.claims.pop(fingerprint, None)


class FakeSound:
    def __init__(self) -> None:
        self.calls = 0

    def play_new_alert(self) -> None:
        self.calls += 1


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
        "starts_at": NOW - timedelta(minutes=30),
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
    sound: FakeSound | None = None,
) -> PollMonitorsUseCase:
    return PollMonitorsUseCase(
        server_config=FakeServerConfig([_server()]),
        monitor_client=FakeMonitorClient(alerts),
        alert_sink=sink,
        clock=clock or FakeClock(),
        dispatch_ledger=ledger,
        alert_sound=sound,
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
    assert ledger.confirmed == [fingerprint_for(alert)]
    sink2 = FakeAlertSink()
    second = _use_case(alerts=[alert], sink=sink2, ledger=ledger).execute()
    assert second.claimed_count == 0
    assert second.skipped_duplicate_count == 1
    assert sink2.calls == 0


def test_ledger_skips_duplicate_even_when_desc_and_status_fluctuate() -> None:
    first_alert = _alert(
        desc="WARNING: 14980031kb used",
        status_text="WARNING: 14980031kb used",
        duration_str="0d 0h 55m 25s",
    )
    second_alert = _alert(
        desc="WARNING: 15011996kb used",
        status_text="WARNING: 15011996kb used",
        duration_str="0d 1h 0m 58s",
    )
    ledger = FakeLedger()
    sink = FakeAlertSink()
    first_cycle = _use_case(alerts=[first_alert], sink=sink, ledger=ledger).execute()
    assert first_cycle.claimed_count == 1
    assert sink.published == [first_alert]
    assert ledger.confirmed == [fingerprint_for(first_alert)]
    assert fingerprint_for(first_alert) == fingerprint_for(second_alert)
    sink2 = FakeAlertSink()
    second_cycle = _use_case(alerts=[second_alert], sink=sink2, ledger=ledger).execute()
    assert second_cycle.claimed_count == 0
    assert second_cycle.skipped_duplicate_count == 1
    assert sink2.calls == 0


def test_ledger_does_not_reclaim_after_window() -> None:
    alert = _alert()
    ledger = FakeLedger()
    clock = FakeClock()
    _use_case(
        alerts=[alert], sink=FakeAlertSink(), ledger=ledger, clock=clock
    ).execute()
    clock.current = NOW + timedelta(minutes=30)
    sink = FakeAlertSink()
    result = _use_case(alerts=[alert], sink=sink, ledger=ledger, clock=clock).execute()
    assert result.claimed_count == 0
    assert result.skipped_duplicate_count == 1
    assert sink.published == []


def test_sink_failure_releases_claim() -> None:
    alert = _alert()
    ledger = FakeLedger()
    boom = FakeAlertSink(error=RuntimeError("sink"))
    result = _use_case(alerts=[alert], sink=boom, ledger=ledger).execute()
    assert result.claimed_count == 0
    assert ledger.released == [fingerprint_for(alert)]
    assert ledger.confirmed == []
    sink = FakeAlertSink()
    retried = _use_case(alerts=[alert], sink=sink, ledger=ledger).execute()
    assert retried.claimed_count == 1
    assert sink.published == [alert]
    assert ledger.confirmed == [fingerprint_for(alert)]


def test_sink_failure_releases_only_failed_alert() -> None:
    first = _alert(alertname="DiskFull")
    second = _alert(alertname="CPU")
    ledger = FakeLedger()
    sink = FakeAlertSink(error=RuntimeError("sink"), fail_on=2)
    result = _use_case(alerts=[first, second], sink=sink, ledger=ledger).execute()
    assert result.claimed_count == 1
    assert sink.published == [first]
    assert ledger.released == [fingerprint_for(second)]
    assert ledger.confirmed == [fingerprint_for(first)]
    retry = FakeAlertSink()
    second_cycle = _use_case(
        alerts=[first, second],
        sink=retry,
        ledger=ledger,
    ).execute()
    assert second_cycle.claimed_count == 1
    assert retry.published == [second]


def test_intra_cycle_duplicates_claim_once() -> None:
    first = _alert()
    twin = _alert()
    ledger = FakeLedger()
    sink = FakeAlertSink()
    result = _use_case(alerts=[first, twin], sink=sink, ledger=ledger).execute()
    assert result.claimed_count == 1
    assert result.skipped_duplicate_count == 1
    assert sink.published == [first]
    assert sink.calls == 1


def test_dedup_off_publishes_all_effective() -> None:
    keep = _alert()
    twin = _alert()
    sink = FakeAlertSink()
    result = _use_case(alerts=[keep, twin], sink=sink, ledger=None).execute()
    assert result.claimed_count == 2
    assert result.skipped_duplicate_count == 0
    assert sink.published == [keep, twin]


def test_sound_plays_on_new_claim() -> None:
    sound = FakeSound()
    ledger = FakeLedger()
    _use_case(
        alerts=[_alert()], sink=FakeAlertSink(), ledger=ledger, sound=sound
    ).execute()
    assert sound.calls == 1
    _use_case(
        alerts=[_alert()], sink=FakeAlertSink(), ledger=ledger, sound=sound
    ).execute()
    assert sound.calls == 1


def test_sound_skipped_when_sink_fails() -> None:
    sound = FakeSound()
    ledger = FakeLedger()
    result = _use_case(
        alerts=[_alert()],
        sink=FakeAlertSink(error=RuntimeError("sink")),
        ledger=ledger,
        sound=sound,
    ).execute()
    assert result.claimed_count == 0
    assert sound.calls == 0


def test_sound_plays_when_dedup_off_and_effective() -> None:
    sound = FakeSound()
    _use_case(
        alerts=[_alert()],
        sink=FakeAlertSink(),
        ledger=None,
        sound=sound,
    ).execute()
    assert sound.calls == 1


def test_sound_skipped_when_dedup_off_and_empty() -> None:
    sound = FakeSound()
    _use_case(alerts=[], sink=FakeAlertSink(), ledger=None, sound=sound).execute()
    assert sound.calls == 0
