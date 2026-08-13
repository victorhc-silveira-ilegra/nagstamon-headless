from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.entities.errors import DomainValidationError
from domain.entities.severity import Severity


@dataclass(frozen=True, slots=True)
class Alert:
    server: str
    severity: Severity
    alertname: str
    app: str
    desc: str
    status_text: str = ""
    duration_str: str = ""
    starts_at: datetime | None = None
    alert_state: str = ""
    silenced_by: tuple[str, ...] = ()
    inhibited_by: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        server = self.server.strip()
        alertname = self.alertname.strip()
        app = self.app.strip()
        if not server:
            raise DomainValidationError("alert server must not be empty")
        if not alertname:
            raise DomainValidationError("alertname must not be empty")
        if not app:
            raise DomainValidationError("alert app must not be empty")
        object.__setattr__(self, "server", server)
        object.__setattr__(self, "alertname", alertname)
        object.__setattr__(self, "app", app)
        object.__setattr__(self, "desc", self.desc.strip())
        object.__setattr__(self, "status_text", self.status_text.strip())
        object.__setattr__(self, "duration_str", self.duration_str.strip())
        object.__setattr__(self, "alert_state", self.alert_state.strip().lower())

    def dedup_key(self) -> str:
        return f"{self.server}\0{self.alertname}\0{self.app}\0{self.desc}"
