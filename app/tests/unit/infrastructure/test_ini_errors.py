from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from infrastructure.adapters.ini_server_config import IniServerConfigAdapter
from infrastructure.logging.events import MONITOR_CONFIG_FAILED, MONITOR_PING_FAILED


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


def test_ini_set_enabled_missing_conf(caplog: pytest.LogCaptureFixture) -> None:
    adapter = IniServerConfigAdapter(Path("/tmp/missing-nagstamon-dir"), "")
    with caplog.at_level("WARNING"):
        adapter.set_enabled("ghost", False)
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_PING_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_ini_set_enabled_unknown_name(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "server_core.conf").write_text(
        "[S]\nenabled=True\nurl=http://x\n",
        encoding="utf-8",
    )
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="")
    with caplog.at_level("WARNING"):
        adapter.set_enabled("ghost", False)
    assert any(
        getattr(record, "semantic", {}).get("error_type") == "missing_conf"
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_ini_set_enabled_read_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "server_core.conf"
    path.write_text("[S]\nenabled=True\nurl=http://x\n", encoding="utf-8")

    def _boom(*args: object, **kwargs: object) -> str:
        raise OSError("denied")

    monkeypatch.setattr(Path, "read_text", _boom)
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="")
    import logging

    logging.getLogger("infrastructure.adapters.ini_server_config").setLevel(
        logging.DEBUG
    )
    with caplog.at_level("WARNING"):
        adapter.set_enabled("core", False)
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_PING_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_ini_set_enabled_missing_line(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "server_core.conf").write_text(
        "[S]\nurl=http://x\n",
        encoding="utf-8",
    )
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="")
    with caplog.at_level("WARNING"):
        adapter.set_enabled("core", True)
    assert any(
        getattr(record, "semantic", {}).get("error_type") == "missing_enabled"
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_ini_set_enabled_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "server_core.conf"
    path.write_text("[S]\nenabled=True\nurl=http://x\n", encoding="utf-8")

    def _boom(src: object, dst: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("infrastructure.adapters.ini_server_config.os.replace", _boom)
    adapter = IniServerConfigAdapter(tmp_path, default_proxy="")
    import logging

    logging.getLogger("infrastructure.adapters.ini_server_config").setLevel(
        logging.DEBUG
    )
    with caplog.at_level("WARNING"):
        adapter.set_enabled("core", False)
    assert any(
        getattr(record, "semantic", {}).get("event") == MONITOR_PING_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )
    assert not list(tmp_path.glob(".*.tmp"))
