from __future__ import annotations

import logging

import pytest

from infrastructure.logging.emit import log_event


def test_log_event_attaches_semantic_payload(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("emit-test")
    with caplog.at_level(logging.INFO, logger="emit-test"):
        log_event(logger, logging.INFO, "poll.cycle.started", servers_count=1)
    assert caplog.records
    assert caplog.records[0].semantic["event"] == "poll.cycle.started"
    assert caplog.records[0].semantic["servers_count"] == 1
