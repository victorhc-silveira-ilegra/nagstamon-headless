from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from domain.entities.alert import Alert
from domain.services.alert_view import (
    DISPLAY_TIMEZONE,
    format_chat_text,
    render_effective_alerts,
)
from infrastructure.adapters.http_client import USER_AGENT
from infrastructure.logging import (
    POLL_GCHAT_FAILED,
    POLL_GCHAT_PUBLISHED,
    log_event,
    redact_url,
)

logger = logging.getLogger(__name__)


class GoogleChatDeliveryError(RuntimeError):
    pass


class GoogleChatWebhookSink:
    def __init__(
        self,
        webhook_url: str,
        *,
        timeout_seconds: float,
        proxy: str = "",
        timezone: ZoneInfo | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._timezone = timezone or DISPLAY_TIMEZONE
        self._lock = threading.Lock()
        self._client = httpx.Client(
            timeout=timeout_seconds,
            proxy=proxy or None,
            transport=transport,
            headers=USER_AGENT,
        )

    def publish(self, alerts: Sequence[Alert], *, fetched_at: datetime) -> None:
        if not alerts:
            return
        text = format_chat_text(
            render_effective_alerts(alerts, fetched_at, self._timezone)
        )
        with self._lock:
            try:
                response = self._client.post(self._webhook_url, json={"text": text})
            except Exception as exc:
                self._log_failed(type(exc).__name__)
                raise GoogleChatDeliveryError(type(exc).__name__) from exc
            if response.is_success:
                log_event(
                    logger,
                    logging.INFO,
                    POLL_GCHAT_PUBLISHED,
                    alerts_count=len(alerts),
                )
                return
            self._log_failed("http_status", http_status=response.status_code)
            raise GoogleChatDeliveryError("http_status")

    def _log_failed(self, error_type: str, *, http_status: int | None = None) -> None:
        fields: dict[str, object] = {
            "error_type": error_type,
            "webhook_host": redact_url(self._webhook_url),
        }
        if http_status is not None:
            fields["http_status"] = http_status
        log_event(
            logger,
            logging.WARNING,
            POLL_GCHAT_FAILED,
            exc_info=logger.isEnabledFor(logging.DEBUG),
            **fields,
        )
