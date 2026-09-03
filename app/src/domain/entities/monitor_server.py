from __future__ import annotations

from dataclasses import dataclass

from domain.entities.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class MonitorServer:
    name: str
    url: str
    proxy: str
    username: str
    password: str
    server_type: str
    enabled: bool = True

    def __post_init__(self) -> None:
        name = self.name.strip()
        url = self.url.strip()
        if not name:
            raise DomainValidationError("server name must not be empty")
        if not url:
            raise DomainValidationError("server url must not be empty")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "proxy", self.proxy.strip())
        object.__setattr__(self, "username", self.username.strip())
        object.__setattr__(self, "password", self.password)
        object.__setattr__(self, "server_type", self.server_type.strip().lower())
        object.__setattr__(self, "enabled", bool(self.enabled))

    @property
    def is_alertmanager(self) -> bool:
        return "alertmanager" in self.server_type or "alertmanager" in self.name.lower()
