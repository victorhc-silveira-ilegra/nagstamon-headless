from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from infrastructure.adapters.file_alert_dispatch_ledger import (
    FileAlertDispatchLedger,
    _parse_at,
)

NOW = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)


def _ledger(tmp_path: Path, **overrides: object) -> FileAlertDispatchLedger:
    payload: dict[str, object] = {"path": tmp_path / "dispatch-ledger.json"}
    payload.update(overrides)
    return FileAlertDispatchLedger(**payload)  # type: ignore[arg-type]


def test_parse_at_rejects_invalid() -> None:
    assert _parse_at(None) is None
    assert _parse_at("") is None
    assert _parse_at("nope") is None
    assert _parse_at(NOW.isoformat()) == NOW


def test_file_ledger_claims_once_after_confirm(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is False
    ledger.confirm(fingerprint="abc", now=NOW)
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
    assert (
        ledger.try_claim(
            fingerprint="abc", now=NOW + timedelta(days=2), window_minutes=30
        )
        is False
    )


def test_file_ledger_release_allows_reclaim(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True
    ledger.release(fingerprint="abc")
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True


def test_file_ledger_release_unknown_is_noop(tmp_path: Path) -> None:
    _ledger(tmp_path).release(fingerprint="missing")


def test_file_ledger_pending_ttl_allows_reclaim(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, pending_ttl_seconds=120)
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True
    assert (
        ledger.try_claim(
            fingerprint="abc", now=NOW + timedelta(seconds=120), window_minutes=30
        )
        is True
    )


def test_file_ledger_confirm_without_pending(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.confirm(fingerprint="abc", now=NOW)
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is False


def test_file_ledger_corrupt_json_starts_empty(tmp_path: Path) -> None:
    path = tmp_path / "dispatch-ledger.json"
    path.write_text("{not-json", encoding="utf-8")
    ledger = FileAlertDispatchLedger(path)
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True


def test_file_ledger_rejects_non_object_payload(tmp_path: Path) -> None:
    path = tmp_path / "dispatch-ledger.json"
    path.write_text("[]", encoding="utf-8")
    ledger = FileAlertDispatchLedger(path)
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True


def test_file_ledger_skips_invalid_records(tmp_path: Path) -> None:
    path = tmp_path / "dispatch-ledger.json"
    path.write_text(
        json.dumps(
            {
                "bad-status": {"status": "other", "at": NOW.isoformat()},
                "bad-at": {"status": "sent", "at": "nope"},
                "not-record": "x",
            }
        ),
        encoding="utf-8",
    )
    ledger = FileAlertDispatchLedger(path)
    assert ledger.try_claim(fingerprint="bad-at", now=NOW, window_minutes=30) is True
    assert ledger.try_claim(fingerprint="ok", now=NOW, window_minutes=30) is True


def test_file_ledger_binary_file_starts_empty(tmp_path: Path) -> None:
    path = tmp_path / "dispatch-ledger.json"
    path.write_bytes(b"\xff\xfe")
    ledger = FileAlertDispatchLedger(path)
    assert ledger.try_claim(fingerprint="abc", now=NOW, window_minutes=30) is True


def test_file_ledger_thread_race_only_one_wins(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
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
