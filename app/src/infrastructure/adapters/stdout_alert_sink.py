from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from datetime import datetime
from typing import TextIO

from domain.entities.alert import Alert
from infrastructure.logging import POLL_SINK_PUBLISHED, log_event

logger = logging.getLogger(__name__)


class StdoutAlertSink:
    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stdout

    def publish(self, alerts: Sequence[Alert], *, fetched_at: datetime) -> None:
        timestamp = fetched_at.strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{timestamp}] Total de Alertas Efetivos: {len(alerts)}",
            file=self._stream,
        )
        for alert in alerts:
            severity = alert.severity.value
            print(
                f"  [{severity:^7}] {alert.server[:32]:<32} | "
                f"{alert.alertname} ({alert.app}): {alert.desc}",
                file=self._stream,
            )
        print("-" * 100, file=self._stream)
        log_event(
            logger,
            logging.INFO,
            POLL_SINK_PUBLISHED,
            alerts_count=len(alerts),
        )
