from __future__ import annotations

from pathlib import Path

import pytest

from infrastructure.config.dotenv_loader import load_dotenv_file
from infrastructure.config.settings import Settings


def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVERS_DIR", "/tmp/servers")
    monkeypatch.setenv("PROXY_ADDR", "http://proxy.example:3128")
    monkeypatch.setenv("REFRESH_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("HTTP_MAX_WORKERS", "8")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FORMAT", "text")
    monkeypatch.delenv("LOG_FILE", raising=False)
    monkeypatch.delenv("LOG_DIR", raising=False)
    monkeypatch.delenv("GCHAT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("DEDUP_LEDGER_PATH", raising=False)


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_FILE", "logs/nagstamon.log")
    monkeypatch.setenv("LOG_DIR", "logs")
    monkeypatch.setenv("DEDUP_ENABLED", "false")
    monkeypatch.setenv("DEDUP_WINDOW_MINUTES", "45")
    monkeypatch.setenv("WINDOW_START", "14:00")
    monkeypatch.setenv("WINDOW_END", "17:30")
    monkeypatch.setenv("WINDOW_TIMEZONE", "UTC")
    monkeypatch.setenv("WINDOW_DAYS", "mon,wed,fri")
    monkeypatch.setenv("FILTER_HOLD_FAST_SECONDS", "90")
    monkeypatch.setenv("FILTER_HOLD_CRITICAL_SECONDS", "120")
    monkeypatch.setenv("FILTER_HOLD_WARNING_SECONDS", "300")
    monkeypatch.setenv("FILTER_DURATION_MAX_SECONDS", "7200")
    monkeypatch.setenv("SOUND_ENABLED", "false")
    monkeypatch.setenv("GCHAT_WEBHOOK_URL", "https://chat.example/messages?key=k")
    monkeypatch.setenv("DEDUP_LEDGER_PATH", "/tmp/dispatch-ledger.json")
    settings = Settings.from_env()
    assert settings.servers_dir == Path("/tmp/servers")
    assert settings.proxy_addr == "http://proxy.example:3128"
    assert settings.refresh_interval == 30
    assert settings.http_timeout_seconds == 5.0
    assert settings.http_max_workers == 8
    assert settings.log_level == "DEBUG"
    assert settings.log_format == "json"
    assert settings.log_file == "logs/nagstamon.log"
    assert settings.log_dir == Path("logs")
    assert settings.dedup_enabled is False
    assert settings.dedup_window_minutes == 45
    assert settings.filter_window_enabled is True
    assert settings.filter_window_start.hour == 14
    assert settings.filter_window_end.hour == 17
    assert settings.filter_window_end.minute == 30
    assert settings.filter_window_allow_past_active_alerts is False
    assert settings.filter_timezone == "UTC"
    assert settings.filter_weekdays == (0, 2, 4)
    assert settings.filter_hold_fast_seconds == 90
    assert settings.filter_hold_critical_seconds == 120
    assert settings.filter_hold_warning_seconds == 300
    assert settings.filter_duration_max_seconds == 7200
    assert settings.sound_enabled is False
    assert settings.gchat_webhook_url == "https://chat.example/messages?key=k"
    assert settings.dedup_ledger_path == Path("/tmp/dispatch-ledger.json")


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERVERS_DIR", raising=False)
    monkeypatch.delenv("PROXY_ADDR", raising=False)
    monkeypatch.delenv("REFRESH_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("HTTP_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("HTTP_MAX_WORKERS", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    monkeypatch.delenv("LOG_FILE", raising=False)
    monkeypatch.delenv("LOG_DIR", raising=False)
    monkeypatch.delenv("DEDUP_ENABLED", raising=False)
    monkeypatch.delenv("DEDUP_WINDOW_MINUTES", raising=False)
    monkeypatch.delenv("WINDOW_ENABLED", raising=False)
    monkeypatch.delenv("WINDOW_START", raising=False)
    monkeypatch.delenv("WINDOW_END", raising=False)
    monkeypatch.delenv("WINDOW_TIMEZONE", raising=False)
    monkeypatch.delenv("WINDOW_DAYS", raising=False)
    monkeypatch.delenv("WINDOW_ALLOW_PAST_ACTIVE_ALERTS", raising=False)
    monkeypatch.delenv("FILTER_HOLD_FAST_SECONDS", raising=False)
    monkeypatch.delenv("FILTER_HOLD_CRITICAL_SECONDS", raising=False)
    monkeypatch.delenv("FILTER_HOLD_WARNING_SECONDS", raising=False)
    monkeypatch.delenv("FILTER_DURATION_MAX_SECONDS", raising=False)
    monkeypatch.delenv("SOUND_ENABLED", raising=False)
    monkeypatch.delenv("GCHAT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("DEDUP_LEDGER_PATH", raising=False)
    settings = Settings.from_env()
    assert settings.servers_dir == Path("/etc/nagstamon/servers")
    assert settings.proxy_addr == ""
    assert settings.refresh_interval == 30
    assert settings.http_timeout_seconds == 5.0
    assert settings.http_max_workers == 30
    assert settings.log_level == "INFO"
    assert settings.log_format == "text"
    assert settings.log_file is None
    assert settings.log_dir == Path("logs")
    assert settings.dedup_enabled is True
    assert settings.dedup_window_minutes == 30
    assert settings.filter_window_enabled is True
    assert settings.filter_window_start.hour == 13
    assert settings.filter_window_start.minute == 30
    assert settings.filter_window_end.hour == 18
    assert settings.filter_window_end.minute == 0
    assert settings.filter_window_allow_past_active_alerts is False
    assert settings.filter_timezone == "America/Sao_Paulo"
    assert settings.filter_weekdays == (0, 1, 2, 3, 4)
    assert settings.filter_hold_fast_seconds == 600
    assert settings.filter_hold_critical_seconds == 900
    assert settings.filter_hold_warning_seconds == 1200
    assert settings.filter_duration_max_seconds == 86400
    assert settings.sound_enabled is True
    assert settings.gchat_webhook_url == ""
    assert settings.dedup_ledger_path is None


def test_settings_blank_log_level_and_format(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LOG_LEVEL", "  ")
    monkeypatch.setenv("LOG_FORMAT", "  ")
    settings = Settings.from_env()
    assert settings.log_level == "INFO"
    assert settings.log_format == "text"


def test_settings_blank_log_dir_disables_daily_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("LOG_DIR", "  ")
    settings = Settings.from_env()
    assert settings.log_dir is None


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
    monkeypatch.setenv("REFRESH_INTERVAL_SECONDS", "abc")
    with pytest.raises(ValueError, match="REFRESH_INTERVAL_SECONDS"):
        Settings.from_env()


def test_settings_rejects_non_positive_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("REFRESH_INTERVAL_SECONDS", "0")
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
        "SERVERS_DIR=/from-dotenv\nREFRESH_INTERVAL_SECONDS=7\n",
        encoding="utf-8",
    )

    def _load(*, override: bool = False) -> Path:
        load_dotenv_file(env_file, override=override)
        return env_file

    monkeypatch.delenv("NAGSTAMON_DISABLE_DOTENV", raising=False)
    monkeypatch.delenv("SERVERS_DIR", raising=False)
    monkeypatch.delenv("REFRESH_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("PROXY_ADDR", raising=False)
    monkeypatch.delenv("HTTP_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("HTTP_MAX_WORKERS", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    monkeypatch.delenv("LOG_FILE", raising=False)
    monkeypatch.delenv("LOG_DIR", raising=False)
    monkeypatch.delenv("DEDUP_ENABLED", raising=False)
    monkeypatch.delenv("DEDUP_WINDOW_MINUTES", raising=False)
    monkeypatch.delenv("WINDOW_ENABLED", raising=False)
    monkeypatch.delenv("WINDOW_START", raising=False)
    monkeypatch.delenv("WINDOW_END", raising=False)
    monkeypatch.delenv("WINDOW_TIMEZONE", raising=False)
    monkeypatch.delenv("WINDOW_DAYS", raising=False)
    monkeypatch.delenv("WINDOW_START", raising=False)
    monkeypatch.delenv("WINDOW_END", raising=False)
    monkeypatch.delenv("WINDOW_DAYS", raising=False)
    monkeypatch.delenv("WINDOW_TIMEZONE", raising=False)
    monkeypatch.delenv("FILTER_HOLD_FAST_SECONDS", raising=False)
    monkeypatch.delenv("FILTER_HOLD_CRITICAL_SECONDS", raising=False)
    monkeypatch.delenv("FILTER_HOLD_WARNING_SECONDS", raising=False)
    monkeypatch.delenv("FILTER_DURATION_MAX_SECONDS", raising=False)
    monkeypatch.delenv("SOUND_ENABLED", raising=False)
    monkeypatch.delenv("GCHAT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("DEDUP_LEDGER_PATH", raising=False)
    monkeypatch.setattr(
        "infrastructure.config.settings.load_project_dotenv",
        _load,
    )
    settings = Settings.from_env()
    assert settings.servers_dir == Path("/from-dotenv")
    assert settings.refresh_interval == 7
    assert settings.log_dir == Path("logs")


def test_settings_rejects_invalid_filter_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_START", "25:00")
    with pytest.raises(ValueError, match="WINDOW_START"):
        Settings.from_env()


def test_settings_rejects_malformed_filter_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_END", "noon")
    with pytest.raises(ValueError, match="WINDOW_END"):
        Settings.from_env()


def test_settings_blank_filter_window_and_timezone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_START", "  ")
    monkeypatch.setenv("WINDOW_END", "  ")
    monkeypatch.setenv("WINDOW_TIMEZONE", "  ")
    monkeypatch.setenv("WINDOW_DAYS", "  ")
    settings = Settings.from_env()
    assert settings.filter_window_start.hour == 13
    assert settings.filter_window_end.hour == 18
    assert settings.filter_timezone == "America/Sao_Paulo"
    assert settings.filter_weekdays == (0, 1, 2, 3, 4)


def test_settings_parses_portuguese_weekdays(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_DAYS", "seg, ter, qua, qui, sex")
    settings = Settings.from_env()
    assert settings.filter_weekdays == (0, 1, 2, 3, 4)
    monkeypatch.setenv("WINDOW_DAYS", "seg,seg,mon")
    assert Settings.from_env().filter_weekdays == (0,)
    monkeypatch.setenv("WINDOW_DAYS", " , , ")
    assert Settings.from_env().filter_weekdays == (0, 1, 2, 3, 4)


def test_settings_rejects_invalid_weekdays(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_DAYS", "mon,holiday")
    with pytest.raises(ValueError, match="WINDOW_DAYS"):
        Settings.from_env()


def test_settings_rejects_invalid_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_TIMEZONE", "Not/AZone")
    with pytest.raises(ValueError, match="WINDOW_TIMEZONE"):
        Settings.from_env()


def test_settings_rejects_non_numeric_hhmm(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_START", "aa:00")
    with pytest.raises(ValueError, match="WINDOW_START"):
        Settings.from_env()


def test_settings_rejects_invalid_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_END", "12:60")
    with pytest.raises(ValueError, match="WINDOW_END"):
        Settings.from_env()


def test_settings_blank_duration_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("FILTER_HOLD_FAST_SECONDS", "  ")
    monkeypatch.setenv("FILTER_HOLD_CRITICAL_SECONDS", "  ")
    monkeypatch.setenv("FILTER_HOLD_WARNING_SECONDS", "  ")
    monkeypatch.setenv("FILTER_DURATION_MAX_SECONDS", "  ")
    settings = Settings.from_env()
    assert settings.filter_hold_fast_seconds == 600
    assert settings.filter_hold_critical_seconds == 900
    assert settings.filter_hold_warning_seconds == 1200
    assert settings.filter_duration_max_seconds == 86400


def test_settings_rejects_hold_not_less_than_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("FILTER_HOLD_FAST_SECONDS", "60")
    monkeypatch.setenv("FILTER_HOLD_CRITICAL_SECONDS", "60")
    monkeypatch.setenv("FILTER_HOLD_WARNING_SECONDS", "86400")
    monkeypatch.setenv("FILTER_DURATION_MAX_SECONDS", "600")
    with pytest.raises(ValueError, match="FILTER_HOLD_WARNING_SECONDS"):
        Settings.from_env()


def test_settings_canonical_names(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("REFRESH_INTERVAL_SECONDS", "45")
    monkeypatch.setenv("WINDOW_START", "10:00")
    monkeypatch.setenv("WINDOW_END", "16:30")
    monkeypatch.setenv("WINDOW_DAYS", "tue,thu")
    monkeypatch.setenv("WINDOW_TIMEZONE", "UTC")
    monkeypatch.setenv("WINDOW_ENABLED", "false")
    monkeypatch.setenv("GCHAT_WEBHOOK_URL", "https://chat.example/canonical")
    settings = Settings.from_env()
    assert settings.refresh_interval == 45
    assert settings.filter_window_enabled is False
    assert settings.filter_window_start.hour == 10
    assert settings.filter_window_end.hour == 16
    assert settings.filter_window_end.minute == 30
    assert settings.filter_weekdays == (1, 3)
    assert settings.filter_timezone == "UTC"
    assert settings.gchat_webhook_url == "https://chat.example/canonical"


def test_settings_ignores_legacy_names(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.delenv("REFRESH_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("WINDOW_ENABLED", raising=False)
    monkeypatch.delenv("WINDOW_START", raising=False)
    monkeypatch.delenv("GCHAT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("REFRESH_INTERVAL", "90")
    monkeypatch.setenv("FILTER_WINDOW_START", "08:00")
    monkeypatch.setenv("FILTER_ENABLED", "false")
    monkeypatch.setenv("WEBHOOK_URL", "https://chat.example/old")
    settings = Settings.from_env()
    assert settings.refresh_interval == 30
    assert settings.filter_window_enabled is True
    assert settings.filter_window_start.hour == 13
    assert settings.filter_window_start.minute == 30
    assert settings.gchat_webhook_url == ""


def test_settings_morning_shift_defaults_allow_past_alerts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_START", "08:30")
    monkeypatch.setenv("WINDOW_END", "13:30")
    monkeypatch.delenv("WINDOW_ALLOW_PAST_ACTIVE_ALERTS", raising=False)
    settings = Settings.from_env()
    assert settings.filter_window_start.hour == 8
    assert settings.filter_window_start.minute == 30
    assert settings.filter_window_end.hour == 13
    assert settings.filter_window_end.minute == 30
    assert settings.filter_window_allow_past_active_alerts is True


def test_settings_explicit_allow_past_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("WINDOW_START", "13:30")
    monkeypatch.setenv("WINDOW_ALLOW_PAST_ACTIVE_ALERTS", "true")
    assert Settings.from_env().filter_window_allow_past_active_alerts is True
    monkeypatch.setenv("WINDOW_START", "08:30")
    monkeypatch.setenv("WINDOW_ALLOW_PAST_ACTIVE_ALERTS", "false")
    assert Settings.from_env().filter_window_allow_past_active_alerts is False
