from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from domain.entities.alert import Alert
from domain.entities.monitor_server import MonitorServer


class MonitorClientPort(Protocol):
    def fetch_all(self, servers: Sequence[MonitorServer]) -> Sequence[Alert]: ...
