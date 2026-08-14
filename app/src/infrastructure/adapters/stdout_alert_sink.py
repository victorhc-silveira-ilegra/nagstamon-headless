from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from datetime import datetime
from typing import TextIO
from zoneinfo import ZoneInfo

from domain.entities.alert import Alert
from domain.services.alert_view import DISPLAY_TIMEZONE, render_effective_alerts
from infrastructure.logging import POLL_SINK_PUBLISHED, log_event

logger = logging.getLogger(__name__)


class StdoutAlertSink:
    def __init__(
        self,
        stream: TextIO | None = None,
        timezone: ZoneInfo | None = None,
    ) -> None:
        self._stream = stream or sys.stdout
        self._timezone = timezone or DISPLAY_TIMEZONE

    def publish(self, alerts: Sequence[Alert], *, fetched_at: datetime) -> None:
        print(
            render_effective_alerts(alerts, fetched_at, self._timezone),
            file=self._stream,
            flush=True,
        )
        log_event(
            logger,
            logging.INFO,
            POLL_SINK_PUBLISHED,
            alerts_count=len(alerts),
        )
