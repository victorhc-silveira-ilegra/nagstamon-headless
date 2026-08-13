from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from application.ports.alert_dispatch_ledger import AlertDispatchLedgerPort
from application.ports.alert_sink import AlertSinkPort
from application.ports.clock import ClockPort
from application.ports.monitor_client import MonitorClientPort
from application.ports.server_config import ServerConfigPort
from domain.entities.alert import Alert
from domain.services.alert_filter import AlertFilterPolicy


@dataclass(frozen=True, slots=True)
class PollCycleResult:
    servers_count: int
    alerts_count: int
    claimed_count: int = 0
    skipped_duplicate_count: int = 0


def fingerprint_for(alert: Alert) -> str:
    return hashlib.sha256(alert.dedup_key().encode()).hexdigest()


def _unique_by_dedup_key(alerts: Sequence[Alert]) -> tuple[list[Alert], int]:
    seen: set[str] = set()
    unique: list[Alert] = []
    for alert in alerts:
        key = alert.dedup_key()
        if key in seen:
            continue
        seen.add(key)
        unique.append(alert)
    return unique, len(alerts) - len(unique)


class PollMonitorsUseCase:
    def __init__(
        self,
        server_config: ServerConfigPort,
        monitor_client: MonitorClientPort,
        alert_sink: AlertSinkPort,
        clock: ClockPort,
        filter_policy: AlertFilterPolicy | None = None,
        dispatch_ledger: AlertDispatchLedgerPort | None = None,
        dedup_window_minutes: int = 30,
    ) -> None:
        self._server_config = server_config
        self._monitor_client = monitor_client
        self._alert_sink = alert_sink
        self._clock = clock
        self._filter_policy = filter_policy or AlertFilterPolicy()
        self._dispatch_ledger = dispatch_ledger
        self._dedup_window_minutes = dedup_window_minutes

    def execute(self) -> PollCycleResult:
        servers = list(self._server_config.list_enabled())
        raw_alerts = list(self._monitor_client.fetch_all(servers))
        now = self._clock.now()
        effective = self._filter_policy.apply(raw_alerts, now)
        if self._dispatch_ledger is None:
            self._alert_sink.publish(effective, fetched_at=now)
            return PollCycleResult(
                servers_count=len(servers),
                alerts_count=len(effective),
                claimed_count=len(effective),
                skipped_duplicate_count=0,
            )
        unique, intra_skipped = _unique_by_dedup_key(effective)
        claimed: list[Alert] = []
        claimed_fingerprints: list[str] = []
        skipped = intra_skipped
        for alert in unique:
            fingerprint = fingerprint_for(alert)
            if self._dispatch_ledger.try_claim(
                fingerprint=fingerprint,
                now=now,
                window_minutes=self._dedup_window_minutes,
            ):
                claimed.append(alert)
                claimed_fingerprints.append(fingerprint)
            else:
                skipped += 1
        if claimed:
            try:
                self._alert_sink.publish(claimed, fetched_at=now)
            except Exception:
                for fingerprint in claimed_fingerprints:
                    self._dispatch_ledger.release(fingerprint=fingerprint)
                raise
        return PollCycleResult(
            servers_count=len(servers),
            alerts_count=len(effective),
            claimed_count=len(claimed),
            skipped_duplicate_count=skipped,
        )
