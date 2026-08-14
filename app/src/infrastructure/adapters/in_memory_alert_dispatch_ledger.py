from __future__ import annotations

import threading
from datetime import datetime, timedelta


class InMemoryAlertDispatchLedger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._claims: dict[str, datetime] = {}

    def try_claim(
        self,
        *,
        fingerprint: str,
        now: datetime,
        window_minutes: int,
    ) -> bool:
        with self._lock:
            cutoff = now - timedelta(minutes=window_minutes)
            expired = [
                key for key, claimed_at in self._claims.items() if claimed_at <= cutoff
            ]
            for key in expired:
                del self._claims[key]
            claimed_at = self._claims.get(fingerprint)
            if claimed_at is not None:
                return False
            self._claims[fingerprint] = now
            return True

    def confirm(self, *, fingerprint: str, now: datetime) -> None:
        with self._lock:
            if fingerprint in self._claims:
                self._claims[fingerprint] = now

    def release(self, *, fingerprint: str) -> None:
        with self._lock:
            self._claims.pop(fingerprint, None)
