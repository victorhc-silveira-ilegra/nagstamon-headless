from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from application.ports.alert_dispatch_ledger import AlertDispatchLedgerPort
from application.ports.alert_sink import AlertSinkPort
from application.ports.alert_sound import AlertSoundPort
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
        alert_sound: AlertSoundPort | None = None,
        dedup_window_minutes: int = 30,
    ) -> None:
        self._server_config = server_config
        self._monitor_client = monitor_client
        self._alert_sink = alert_sink
        self._clock = clock
        self._filter_policy = filter_policy or AlertFilterPolicy()
        self._dispatch_ledger = dispatch_ledger
        self._alert_sound = alert_sound
        self._dedup_window_minutes = dedup_window_minutes

    def _play_new_alert(self) -> None:
        if self._alert_sound is not None:
            self._alert_sound.play_new_alert()

    def execute(self) -> PollCycleResult:
        servers = list(self._server_config.list_enabled())
        raw_alerts = list(self._monitor_client.fetch_all(servers))
        now = self._clock.now()
        effective = self._filter_policy.apply(raw_alerts, now)
        if self._dispatch_ledger is None:
            self._alert_sink.publish(effective, fetched_at=now)
            if effective:
                self._play_new_alert()
            return PollCycleResult(
                servers_count=len(servers),
                alerts_count=len(effective),
                claimed_count=len(effective),
                skipped_duplicate_count=0,
            )
        unique, intra_skipped = _unique_by_dedup_key(effective)
        claimed: list[Alert] = []
        skipped = intra_skipped
        for alert in unique:
            fingerprint = fingerprint_for(alert)
            if not self._dispatch_ledger.try_claim(
                fingerprint=fingerprint,
                now=now,
                window_minutes=self._dedup_window_minutes,
            ):
                skipped += 1
                continue
            try:
                self._alert_sink.publish([alert], fetched_at=now)
            except Exception:
                self._dispatch_ledger.release(fingerprint=fingerprint)
                continue
            self._dispatch_ledger.confirm(fingerprint=fingerprint, now=now)
            claimed.append(alert)
        if claimed:
            self._play_new_alert()
        return PollCycleResult(
            servers_count=len(servers),
            alerts_count=len(effective),
            claimed_count=len(claimed),
            skipped_duplicate_count=skipped,
        )
