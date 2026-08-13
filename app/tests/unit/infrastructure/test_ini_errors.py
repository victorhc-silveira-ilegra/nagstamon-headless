from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from infrastructure.adapters.ini_server_config import IniServerConfigAdapter
from infrastructure.logging.events import MONITOR_CONFIG_FAILED


def test_ini_read_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "x.conf").write_text(
        "[S]\nenabled=True\nurl=http://x\n",
        encoding="utf-8",
    )

    def _boom(self: object, *args: object, **kwargs: object) -> list[str]:
        raise OSError("denied")

    monkeypatch.setattr(
        "infrastructure.adapters.ini_server_config.configparser.ConfigParser.read",
        _boom,
    )
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="")
    with caplog.at_level("WARNING"):
        assert adapter.list_enabled() == []
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_CONFIG_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_ini_read_parser_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "x.conf").write_text(
        "[S]\nenabled=True\nurl=http://x\n",
        encoding="utf-8",
    )

    def _boom(self: object, *args: object, **kwargs: object) -> list[str]:
        raise configparser.Error("bad")

    monkeypatch.setattr(
        "infrastructure.adapters.ini_server_config.configparser.ConfigParser.read",
        _boom,
    )
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="")
    import logging

    logging.getLogger("infrastructure.adapters.ini_server_config").setLevel(
        logging.DEBUG
    )
    assert adapter.list_enabled() == []
