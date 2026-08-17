from __future__ import annotations

import threading
from datetime import datetime


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
        _ = window_minutes
        with self._lock:
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
