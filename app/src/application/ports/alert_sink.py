from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from domain.entities.alert import Alert


class AlertSinkPort(Protocol):
    def publish(self, alerts: Sequence[Alert], *, fetched_at: datetime) -> None: ...
