from __future__ import annotations

from infrastructure.logging.redact import redact_url, truncate_preview


def test_redact_url_masks_query() -> None:
    url = "https://monitor.example/api?token=secret&user=admin"
    redacted = redact_url(url)
    assert "secret" not in redacted
    assert "admin" not in redacted
    assert redacted.endswith("?***")
    assert "monitor.example" in redacted


def test_redact_url_without_query() -> None:
    url = "http://alertmanager.example/api/v2/alerts"
    assert redact_url(url) == url


def test_truncate_preview_short() -> None:
    assert truncate_preview("ok") == "ok"


def test_truncate_preview_long() -> None:
    value = "x" * 100
    preview = truncate_preview(value, max_len=80)
    assert len(preview) == 80
    assert preview.endswith("...")
