from __future__ import annotations

import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from domain.entities.alert import Alert
from domain.entities.monitor_server import MonitorServer
from infrastructure.adapters.alertmanager_http import AlertmanagerHttpClient
from infrastructure.adapters.http_client import log_fetch_failed
from infrastructure.adapters.nagios_cgi_http import NagiosCgiHttpClient


class CompositeMonitorClient:
    def __init__(
        self,
        alertmanager: AlertmanagerHttpClient,
        nagios: NagiosCgiHttpClient,
        max_workers: int = 30,
    ) -> None:
        self._alertmanager = alertmanager
        self._nagios = nagios
        self._max_workers = max(1, max_workers)

    def fetch_all(self, servers: Sequence[MonitorServer]) -> list[Alert]:
        if not servers:
            return []
        workers = min(self._max_workers, len(servers))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            chunks = list(pool.map(self._fetch_one, servers))
        collected: list[Alert] = []
        for chunk in chunks:
            collected.extend(chunk)
        return collected

    def _fetch_one(self, server: MonitorServer) -> list[Alert]:
        try:
            if server.is_alertmanager:
                return list(self._alertmanager.fetch(server))
            return list(self._nagios.fetch(server))
        except Exception:
            log_fetch_failed(
                server,
                error_type="unexpected",
                exc_info=logging.getLogger(__name__).isEnabledFor(logging.DEBUG),
            )
            return []
