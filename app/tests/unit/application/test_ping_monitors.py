from __future__ import annotations

from collections.abc import Sequence

from application.use_cases.ping_monitors import PingMonitorsUseCase
from domain.entities.monitor_server import MonitorServer


class FakeServerConfig:
    def __init__(self, servers: Sequence[MonitorServer]) -> None:
        self._servers = list(servers)
        self.enabled_calls: list[tuple[str, bool]] = []

    def list_enabled(self) -> Sequence[MonitorServer]:
        return [item for item in self._servers if item.enabled]

    def list_all(self) -> Sequence[MonitorServer]:
        return list(self._servers)

    def set_enabled(self, name: str, enabled: bool) -> None:
        self.enabled_calls.append((name, enabled))
        updated: list[MonitorServer] = []
        for item in self._servers:
            if item.name == name:
                updated.append(
                    MonitorServer(
                        name=item.name,
                        url=item.url,
                        proxy=item.proxy,
                        username=item.username,
                        password=item.password,
                        server_type=item.server_type,
                        enabled=enabled,
                    )
                )
            else:
                updated.append(item)
        self._servers = updated


class FakeProbe:
    def __init__(self, results: dict[str, bool] | None = None) -> None:
        self.results = results or {}
        self.seen: list[str] = []

    def probe(self, server: MonitorServer) -> bool:
        self.seen.append(server.name)
        return self.results.get(server.name, False)


def _server(
    name: str,
    *,
    enabled: bool = True,
    server_type: str = "nagios",
) -> MonitorServer:
    return MonitorServer(
        name=name,
        url=f"http://{name}.example",
        proxy="",
        username="",
        password="",
        server_type=server_type,
        enabled=enabled,
    )


def test_ping_empty_list() -> None:
    use_case = PingMonitorsUseCase(
        server_config=FakeServerConfig([]),
        probe=FakeProbe(),
        max_workers=0,
    )
    result = use_case.execute()
    assert result.servers_count == 0
    assert result.reachable == 0
    assert result.unreachable == 0
    assert result.updated == 0
    assert result.unchanged == 0


def test_ping_updates_and_leaves_unchanged() -> None:
    config = FakeServerConfig(
        [
            _server("up", enabled=False),
            _server("down", enabled=True),
            _server("same-up", enabled=True),
            _server("same-down", enabled=False),
        ]
    )
    probe = FakeProbe(
        {
            "up": True,
            "down": False,
            "same-up": True,
            "same-down": False,
        }
    )
    result = PingMonitorsUseCase(
        server_config=config,
        probe=probe,
        max_workers=4,
    ).execute()
    assert result.servers_count == 4
    assert result.reachable == 2
    assert result.unreachable == 2
    assert result.updated == 2
    assert result.unchanged == 2
    assert sorted(config.enabled_calls) == [("down", False), ("up", True)]
    assert set(probe.seen) == {"up", "down", "same-up", "same-down"}
