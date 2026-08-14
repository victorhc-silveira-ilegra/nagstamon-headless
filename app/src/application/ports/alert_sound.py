from __future__ import annotations

from typing import Protocol


class AlertSoundPort(Protocol):
    def play_new_alert(self) -> None: ...
