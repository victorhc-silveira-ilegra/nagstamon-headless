from __future__ import annotations

import threading


class CycleGuard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._busy = False

    def try_enter(self) -> bool:
        with self._lock:
            if self._busy:
                return False
            self._busy = True
            return True

    def exit(self) -> None:
        with self._lock:
            self._busy = False
