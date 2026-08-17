from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from infrastructure.adapters.in_memory_alert_dispatch_ledger import (
    InMemoryAlertDispatchLedger,
)

NOW = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)


def test_memory_ledger_claims_once() -> None:
    ledger = InMemoryAlertDispatchLedger()
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True
    assert (
        ledger.try_claim(
            fingerprint="abc", now=NOW + timedelta(minutes=29), window_minutes=30
        )
        is False
    )
    assert (
        ledger.try_claim(
            fingerprint="abc", now=NOW + timedelta(minutes=30), window_minutes=30
        )
        is False
    )


def test_memory_ledger_release_allows_reclaim() -> None:
    ledger = InMemoryAlertDispatchLedger()
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True
    ledger.release(fingerprint="abc")
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True


def test_memory_ledger_release_unknown_is_noop() -> None:
    InMemoryAlertDispatchLedger().release(fingerprint="missing")


def test_memory_ledger_confirm_refreshes_timestamp() -> None:
    ledger = InMemoryAlertDispatchLedger()
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True
    later = NOW + timedelta(minutes=10)
    ledger.confirm(fingerprint="abc", now=later)
    ledger.confirm(fingerprint="missing", now=later)
    assert (
        ledger.try_claim(
            fingerprint="abc", now=later + timedelta(minutes=19), window_minutes=30
        )
        is False
    )


def test_memory_ledger_thread_race_only_one_wins() -> None:
    ledger = InMemoryAlertDispatchLedger()
    results: list[bool] = []
    barrier = threading.Barrier(8)

    def _claim() -> None:
        barrier.wait()
        results.append(ledger.try_claim(fingerprint="same", now=NOW, window_minutes=30))

    threads = [threading.Thread(target=_claim) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count(True) == 1
    assert results.count(False) == 7


def test_memory_ledger_keeps_stale_fingerprints() -> None:
    ledger = InMemoryAlertDispatchLedger()
    assert ledger.try_claim(fingerprint="old", now=NOW, window_minutes=30) is True
    later = NOW + timedelta(minutes=30)
    assert ledger.try_claim(fingerprint="new", now=later, window_minutes=30) is True
    assert ledger.try_claim(fingerprint="old", now=later, window_minutes=30) is False
