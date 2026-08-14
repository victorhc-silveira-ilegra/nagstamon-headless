from __future__ import annotations

from datetime import datetime
from typing import Protocol


class AlertDispatchLedgerPort(Protocol):
    def try_claim(
        self,
        *,
        fingerprint: str,
        now: datetime,
        window_minutes: int,
    ) -> bool: ...

    def confirm(self, *, fingerprint: str, now: datetime) -> None: ...

    def release(self, *, fingerprint: str) -> None: ...
