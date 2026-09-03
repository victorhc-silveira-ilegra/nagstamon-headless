from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from domain.entities.monitor_server import MonitorServer


class ServerConfigPort(Protocol):
    def list_enabled(self) -> Sequence[MonitorServer]: ...

    def list_all(self) -> Sequence[MonitorServer]: ...

    def set_enabled(self, name: str, enabled: bool) -> None: ...
