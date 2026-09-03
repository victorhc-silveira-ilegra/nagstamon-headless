from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from application.ports.monitor_probe import MonitorProbePort
from application.ports.server_config import ServerConfigPort


@dataclass(frozen=True, slots=True)
class PingMonitorsResult:
    servers_count: int
    reachable: int
    unreachable: int
    updated: int
    unchanged: int


class PingMonitorsUseCase:
    def __init__(
        self,
        server_config: ServerConfigPort,
        probe: MonitorProbePort,
        max_workers: int,
    ) -> None:
        self._server_config = server_config
        self._probe = probe
        self._max_workers = max(1, max_workers)

    def execute(self) -> PingMonitorsResult:
        servers = list(self._server_config.list_all())
        if not servers:
            return PingMonitorsResult(
                servers_count=0,
                reachable=0,
                unreachable=0,
                updated=0,
                unchanged=0,
            )
        reachable = 0
        unreachable = 0
        updated = 0
        unchanged = 0
        workers = min(self._max_workers, len(servers))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._probe.probe, server): server for server in servers
            }
            for future in as_completed(futures):
                server = futures[future]
                ok = future.result()
                if ok:
                    reachable += 1
                else:
                    unreachable += 1
                if server.enabled == ok:
                    unchanged += 1
                else:
                    self._server_config.set_enabled(server.name, ok)
                    updated += 1
        return PingMonitorsResult(
            servers_count=len(servers),
            reachable=reachable,
            unreachable=unreachable,
            updated=updated,
            unchanged=unchanged,
        )
