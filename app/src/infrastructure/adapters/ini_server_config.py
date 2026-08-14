from __future__ import annotations

import configparser
import logging
from pathlib import Path

from domain.entities.errors import DomainValidationError
from domain.entities.monitor_server import MonitorServer
from infrastructure.adapters.nagstamon_secret import deobfuscate
from infrastructure.logging import MONITOR_CONFIG_FAILED, log_event, redact_url

logger = logging.getLogger(__name__)


class IniServerConfigAdapter:
    def __init__(self, servers_dir: Path, default_proxy: str) -> None:
        self._servers_dir = servers_dir
        self._default_proxy = default_proxy

    def list_enabled(self) -> list[MonitorServer]:
        if not self._servers_dir.exists():
            return []
        servers: list[MonitorServer] = []
        for path in sorted(self._servers_dir.iterdir()):
            if path.suffix != ".conf" or not path.is_file():
                continue
            servers.extend(self._read_file(path))
        return servers

    def _read_file(self, path: Path) -> list[MonitorServer]:
        parser = configparser.ConfigParser(interpolation=None)
        try:
            read_ok = parser.read(path, encoding="utf-8")
        except (OSError, configparser.Error, UnicodeDecodeError):
            log_event(
                logger,
                logging.WARNING,
                MONITOR_CONFIG_FAILED,
                config_file=path.name,
                error_type="read",
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            return []
        if not read_ok:
            log_event(
                logger,
                logging.WARNING,
                MONITOR_CONFIG_FAILED,
                config_file=path.name,
                error_type="empty",
            )
            return []
        name = path.name.replace("server_", "").replace(".conf", "")
        collected: list[MonitorServer] = []
        for section in parser.sections():
            try:
                if not parser.getboolean(section, "enabled", fallback=False):
                    continue
                url = parser.get(
                    section,
                    "monitor_url",
                    fallback=parser.get(section, "url", fallback=""),
                )
                if not url.strip():
                    continue
                proxy = parser.get(
                    section, "proxy_address", fallback=self._default_proxy
                )
                collected.append(
                    MonitorServer(
                        name=name,
                        url=url,
                        proxy=proxy,
                        username=deobfuscate(
                            parser.get(section, "username", fallback="")
                        ),
                        password=deobfuscate(
                            parser.get(section, "password", fallback="")
                        ),
                        server_type=parser.get(section, "type", fallback=""),
                    )
                )
            except (ValueError, configparser.Error, DomainValidationError):
                log_event(
                    logger,
                    logging.WARNING,
                    MONITOR_CONFIG_FAILED,
                    config_file=path.name,
                    monitor_host=redact_url(path.as_posix()),
                    error_type="section",
                    exc_info=logger.isEnabledFor(logging.DEBUG),
                )
        return collected
