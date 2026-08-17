from __future__ import annotations

import fcntl
import json
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import TextIO

PENDING_TTL_SECONDS = 120
STATUS_PENDING = "pending"
STATUS_SENT = "sent"
Record = dict[str, str]
Store = dict[str, Record]


def _parse_at(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


class FileAlertDispatchLedger:
    def __init__(
        self,
        path: Path,
        *,
        pending_ttl_seconds: int = PENDING_TTL_SECONDS,
    ) -> None:
        self._path = path
        self._lock_path = path.with_name(path.name + ".lock")
        self._pending_ttl_seconds = pending_ttl_seconds
        self._lock = threading.Lock()

    @contextmanager
    def _exclusive(self) -> Iterator[TextIO]:
        with self._lock:
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock_path.open("a+", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield handle
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load(self) -> Store:
        if not self._path.is_file():
            return {}
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        records: Store = {}
        for key, value in payload.items():
            if not isinstance(value, dict):
                continue
            status = value.get("status")
            at = value.get("at")
            if (
                isinstance(key, str)
                and status in {STATUS_PENDING, STATUS_SENT}
                and isinstance(at, str)
            ):
                records[key] = {"status": status, "at": at}
        return records

    def _dump(self, records: Store) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text(json.dumps(records, ensure_ascii=True), encoding="utf-8")
        os.replace(tmp, self._path)

    def _prune(self, records: Store, *, now: datetime) -> Store:
        pending_cutoff = now - timedelta(seconds=self._pending_ttl_seconds)
        kept: Store = {}
        for key, record in records.items():
            instant = _parse_at(record.get("at"))
            if instant is None:
                continue
            status = record.get("status")
            if status == STATUS_PENDING and instant <= pending_cutoff:
                continue
            kept[key] = record
        return kept

    def try_claim(
        self,
        *,
        fingerprint: str,
        now: datetime,
        window_minutes: int,
    ) -> bool:
        _ = window_minutes
        with self._exclusive():
            records = self._prune(
                self._load(),
                now=now,
            )
            if fingerprint in records:
                return False
            records[fingerprint] = {
                "status": STATUS_PENDING,
                "at": now.isoformat(),
            }
            self._dump(records)
            return True

    def confirm(self, *, fingerprint: str, now: datetime) -> None:
        with self._exclusive():
            records = self._load()
            records[fingerprint] = {"status": STATUS_SENT, "at": now.isoformat()}
            self._dump(records)

    def release(self, *, fingerprint: str) -> None:
        with self._exclusive():
            records = self._load()
            records.pop(fingerprint, None)
            self._dump(records)
