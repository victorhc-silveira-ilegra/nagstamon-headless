from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from domain.entities.alert import Alert
from domain.entities.severity import Severity
from domain.services.alert_view import (
    DISPLAY_TIMEZONE,
    format_chat_text,
    render_effective_alerts,
)
from infrastructure.adapters.google_chat_http import (
    GoogleChatDeliveryError,
    GoogleChatWebhookSink,
)
from infrastructure.logging.events import POLL_GCHAT_FAILED, POLL_GCHAT_PUBLISHED

NOW = datetime(2026, 8, 14, 17, 0, 0, tzinfo=UTC)
WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAA/messages?key=secret&token=token"


class _Transport(httpx.BaseTransport):
    def __init__(
        self,
        status_code: int = 200,
        error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = error
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return httpx.Response(self.status_code, json={"name": "spaces/AAA/messages/1"})


def _alert() -> Alert:
    return Alert(
        server="core",
        severity=Severity("critical"),
        alertname="DiskFull",
        app="db01",
        desc="disk is full",
        status_text="filesystem /var is 95 percent full",
        host="db01.prod",
        starts_at=NOW - timedelta(hours=2, minutes=15),
    )


def _sink(transport: _Transport, **overrides: object) -> GoogleChatWebhookSink:
    payload: dict[str, object] = {
        "timeout_seconds": 5.0,
        "transport": transport,
    }
    payload.update(overrides)
    return GoogleChatWebhookSink(WEBHOOK, **payload)  # type: ignore[arg-type]


def _gchat_logger() -> logging.Logger:
    return logging.getLogger("infrastructure.adapters.google_chat_http")


def _has_event(caplog: pytest.LogCaptureFixture, event: str) -> bool:
    return any(
        getattr(record, "semantic", {}).get("event") == event
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_gchat_skips_empty_snapshot() -> None:
    transport = _Transport()
    _sink(transport).publish([], fetched_at=NOW)
    assert transport.requests == []


def test_gchat_posts_same_card_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = _Transport()
    alert = _alert()
    with caplog.at_level("INFO"):
        _sink(transport, timezone=DISPLAY_TIMEZONE).publish([alert], fetched_at=NOW)
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert str(request.url).startswith("https://chat.googleapis.com/")
    body = json.loads(request.content)
    expected = format_chat_text(render_effective_alerts([alert], NOW, DISPLAY_TIMEZONE))
    assert body == {"text": expected}
    assert body["text"].startswith("```\n")
    assert "*Client:*" in body["text"]
    assert "core" in body["text"]
    assert _has_event(caplog, POLL_GCHAT_PUBLISHED)
    assert not _has_event(caplog, POLL_GCHAT_FAILED)


def test_gchat_http_error_fail_open(caplog: pytest.LogCaptureFixture) -> None:
    transport = _Transport(status_code=500)
    with caplog.at_level("WARNING"), pytest.raises(GoogleChatDeliveryError):
        _sink(transport).publish([_alert()], fetched_at=NOW)
    assert _has_event(caplog, POLL_GCHAT_FAILED)
    failed = next(
        record
        for record in caplog.records
        if getattr(record, "semantic", {}).get("event") == POLL_GCHAT_FAILED
    )
    host = str(failed.semantic["webhook_host"])
    assert "secret" not in host
    assert "token" not in host
    assert host.endswith("?***")
    assert failed.semantic["http_status"] == 500
    assert failed.semantic["error_type"] == "http_status"


def test_gchat_builds_client_with_proxy() -> None:
    transport = _Transport()
    _sink(transport, proxy="http://proxy.example:3128").publish([], fetched_at=NOW)
    assert transport.requests == []


def test_gchat_request_error_fail_open_debug(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = _Transport(error=httpx.ConnectError("down"))
    gchat_logger = _gchat_logger()
    previous = gchat_logger.level
    gchat_logger.setLevel(logging.DEBUG)
    try:
        with caplog.at_level("DEBUG"), pytest.raises(GoogleChatDeliveryError):
            _sink(transport).publish([_alert()], fetched_at=NOW)
    finally:
        gchat_logger.setLevel(previous)
    assert _has_event(caplog, POLL_GCHAT_FAILED)


def test_gchat_request_error_without_debug(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = _Transport(error=httpx.ConnectError("down"))
    gchat_logger = _gchat_logger()
    previous = gchat_logger.level
    gchat_logger.setLevel(logging.WARNING)
    try:
        with caplog.at_level("WARNING"), pytest.raises(GoogleChatDeliveryError):
            _sink(transport).publish([_alert()], fetched_at=NOW)
    finally:
        gchat_logger.setLevel(previous)
    assert _has_event(caplog, POLL_GCHAT_FAILED)
