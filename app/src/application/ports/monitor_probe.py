from __future__ import annotations

from typing import Protocol

from domain.entities.monitor_server import MonitorServer


class MonitorProbePort(Protocol):
    def probe(self, server: MonitorServer) -> bool: ...
