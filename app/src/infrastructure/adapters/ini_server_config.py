from __future__ import annotations

import configparser
import logging
import os
import re
from pathlib import Path

from domain.entities.errors import DomainValidationError
from domain.entities.monitor_server import MonitorServer
from infrastructure.adapters.nagstamon_secret import deobfuscate
from infrastructure.logging import (
    MONITOR_CONFIG_FAILED,
    MONITOR_PING_FAILED,
    log_event,
    redact_url,
)

logger = logging.getLogger(__name__)
_ENABLED_LINE_RE = re.compile(r"(?im)^([ \t]*enabled[ \t]*=)[^\r\n]*")


class IniServerConfigAdapter:
    def __init__(self, servers_dir: Path, default_proxy: str) -> None:
        self._servers_dir = servers_dir
        self._default_proxy = default_proxy

    def list_enabled(self) -> list[MonitorServer]:
        return self._list(require_enabled=True)

    def list_all(self) -> list[MonitorServer]:
        return self._list(require_enabled=False)

    def set_enabled(self, name: str, enabled: bool) -> None:
        path = self._path_for_name(name)
        if path is None:
            log_event(
                logger,
                logging.WARNING,
                MONITOR_PING_FAILED,
                server_name=name,
                error_type="missing_conf",
            )
            return
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            log_event(
                logger,
                logging.WARNING,
                MONITOR_PING_FAILED,
                server_name=name,
                config_file=path.name,
                error_type=type(exc).__name__,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            return
        value = "True" if enabled else "False"
        new_text, count = _ENABLED_LINE_RE.subn(rf"\g<1>{value}", text)
        if count == 0:
            log_event(
                logger,
                logging.WARNING,
                MONITOR_PING_FAILED,
                server_name=name,
                config_file=path.name,
                error_type="missing_enabled",
            )
            return
        if new_text == text:
            return
        tmp = path.with_name(f".{path.name}.tmp")
        try:
            tmp.write_text(new_text, encoding="utf-8")
            os.replace(tmp, path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            log_event(
                logger,
                logging.WARNING,
                MONITOR_PING_FAILED,
                server_name=name,
                config_file=path.name,
                error_type=type(exc).__name__,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )

    def _list(self, *, require_enabled: bool) -> list[MonitorServer]:
        if not self._servers_dir.exists():
            return []
        servers: list[MonitorServer] = []
        for path in self._conf_files():
            servers.extend(self._read_file(path, require_enabled=require_enabled))
        return servers

    def _conf_files(self) -> list[Path]:
        return sorted(
            path
            for path in self._servers_dir.iterdir()
            if path.suffix == ".conf" and path.is_file()
        )

    def _path_for_name(self, name: str) -> Path | None:
        if not self._servers_dir.exists():
            return None
        for path in self._conf_files():
            if self._server_name(path) == name:
                return path
        return None

    @staticmethod
    def _server_name(path: Path) -> str:
        return path.name.replace("server_", "").replace(".conf", "")

    def _read_file(self, path: Path, *, require_enabled: bool) -> list[MonitorServer]:
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
        name = self._server_name(path)
        collected: list[MonitorServer] = []
        for section in parser.sections():
            try:
                enabled = parser.getboolean(section, "enabled", fallback=False)
                if require_enabled and not enabled:
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
                        enabled=enabled,
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
