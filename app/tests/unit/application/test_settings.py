from __future__ import annotations

from pathlib import Path

import pytest

from infrastructure.config.dotenv_loader import load_dotenv_file
from infrastructure.config.settings import Settings


def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVERS_DIR", "/tmp/servers")
    monkeypatch.setenv("PROXY_ADDR", "http://proxy.example:3128")
    monkeypatch.setenv("REFRESH_INTERVAL", "30")
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("HTTP_MAX_WORKERS", "8")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FORMAT", "text")
    monkeypatch.delenv("LOG_FILE", raising=False)


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_FILE", "logs/nagstamon.log")
    monkeypatch.setenv("DEDUP_ENABLED", "false")
    monkeypatch.setenv("DEDUP_WINDOW_MINUTES", "45")
    settings = Settings.from_env()
    assert settings.servers_dir == Path("/tmp/servers")
    assert settings.proxy_addr == "http://proxy.example:3128"
    assert settings.refresh_interval == 30
    assert settings.http_timeout_seconds == 5.0
    assert settings.http_max_workers == 8
    assert settings.log_level == "DEBUG"
    assert settings.log_format == "json"
    assert settings.log_file == "logs/nagstamon.log"
    assert settings.dedup_enabled is False
    assert settings.dedup_window_minutes == 45


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERVERS_DIR", raising=False)
    monkeypatch.delenv("PROXY_ADDR", raising=False)
    monkeypatch.delenv("REFRESH_INTERVAL", raising=False)
    monkeypatch.delenv("HTTP_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("HTTP_MAX_WORKERS", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    monkeypatch.delenv("LOG_FILE", raising=False)
    monkeypatch.delenv("DEDUP_ENABLED", raising=False)
    monkeypatch.delenv("DEDUP_WINDOW_MINUTES", raising=False)
    settings = Settings.from_env()
    assert settings.servers_dir == Path("/etc/nagstamon/servers")
    assert settings.proxy_addr == ""
    assert settings.refresh_interval == 30
    assert settings.http_timeout_seconds == 5.0
    assert settings.http_max_workers == 30
    assert settings.log_level == "INFO"
    assert settings.log_format == "text"
    assert settings.log_file is None
    assert settings.dedup_enabled is True
    assert settings.dedup_window_minutes == 30


def test_settings_blank_log_level_and_format(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LOG_LEVEL", "  ")
    monkeypatch.setenv("LOG_FORMAT", "  ")
    settings = Settings.from_env()
    assert settings.log_level == "INFO"
    assert settings.log_format == "text"


def test_settings_rejects_invalid_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "abc")
    with pytest.raises(ValueError, match="HTTP_TIMEOUT_SECONDS"):
        Settings.from_env()


def test_settings_rejects_non_positive_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "0")
    with pytest.raises(ValueError, match="greater than zero"):
        Settings.from_env()


def test_settings_rejects_invalid_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("REFRESH_INTERVAL", "abc")
    with pytest.raises(ValueError, match="REFRESH_INTERVAL"):
        Settings.from_env()


def test_settings_rejects_non_positive_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("REFRESH_INTERVAL", "0")
    with pytest.raises(ValueError, match="greater than zero"):
        Settings.from_env()


def test_settings_rejects_invalid_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("HTTP_MAX_WORKERS", "nope")
    with pytest.raises(ValueError, match="HTTP_MAX_WORKERS"):
        Settings.from_env()


def test_settings_rejects_non_positive_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("HTTP_MAX_WORKERS", "-1")
    with pytest.raises(ValueError, match="greater than zero"):
        Settings.from_env()


def test_settings_rejects_invalid_log_format(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LOG_FORMAT", "xml")
    with pytest.raises(ValueError, match="LOG_FORMAT"):
        Settings.from_env()


def test_settings_rejects_invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LOG_LEVEL", "NOPE")
    with pytest.raises(ValueError, match="LOG_LEVEL"):
        Settings.from_env()


def test_settings_rejects_invalid_dedup_window(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("DEDUP_WINDOW_MINUTES", "abc")
    with pytest.raises(ValueError, match="DEDUP_WINDOW_MINUTES"):
        Settings.from_env()


def test_settings_rejects_non_positive_dedup_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("DEDUP_WINDOW_MINUTES", "0")
    with pytest.raises(ValueError, match="greater than zero"):
        Settings.from_env()


def test_settings_loads_dotenv_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SERVERS_DIR=/from-dotenv\nREFRESH_INTERVAL=7\n",
        encoding="utf-8",
    )

    def _load(*, override: bool = False) -> Path:
        load_dotenv_file(env_file, override=override)
        return env_file

    monkeypatch.delenv("NAGSTAMON_DISABLE_DOTENV", raising=False)
    monkeypatch.delenv("SERVERS_DIR", raising=False)
    monkeypatch.delenv("REFRESH_INTERVAL", raising=False)
    monkeypatch.delenv("PROXY_ADDR", raising=False)
    monkeypatch.delenv("HTTP_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("HTTP_MAX_WORKERS", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    monkeypatch.delenv("LOG_FILE", raising=False)
    monkeypatch.delenv("DEDUP_ENABLED", raising=False)
    monkeypatch.delenv("DEDUP_WINDOW_MINUTES", raising=False)
    monkeypatch.setattr(
        "infrastructure.config.settings.load_project_dotenv",
        _load,
    )
    settings = Settings.from_env()
    assert settings.servers_dir == Path("/from-dotenv")
    assert settings.refresh_interval == 7
