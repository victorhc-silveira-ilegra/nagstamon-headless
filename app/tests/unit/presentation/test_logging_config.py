from __future__ import annotations

import logging
from pathlib import Path

from presentation.logging.config import reset_logging_state, setup_logging


def test_setup_logging_text_and_silence_httpx(tmp_path: Path) -> None:
    reset_logging_state()
    log_file = tmp_path / "app.log"
    setup_logging(level="INFO", log_format="text", log_file=str(log_file))
    root = logging.getLogger()
    assert root.level == logging.INFO
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    assert log_file.parent.exists()
    logging.getLogger("demo").info("ping")
    assert log_file.read_text(encoding="utf-8")
    reset_logging_state()


def test_setup_logging_json_and_unknown_level() -> None:
    reset_logging_state()
    setup_logging(level="NOPE", log_format="json", log_file=None)
    assert logging.getLogger().level == logging.INFO
    reset_logging_state()
    setup_logging(level="DEBUG", log_format="json", log_file=None)
    assert logging.getLogger().level == logging.DEBUG
    reset_logging_state()
