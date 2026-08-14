from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from infrastructure.adapters.popen_alert_sound import PopenAlertSound
from infrastructure.logging.events import POLL_SOUND_FAILED


def test_sound_missing_player_fail_open(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "infrastructure.adapters.popen_alert_sound.which",
        lambda _name: None,
    )
    with caplog.at_level("WARNING"):
        PopenAlertSound().play_new_alert()
    assert any(
        getattr(record, "semantic", {}).get("event") == POLL_SOUND_FAILED
        and record.levelno == logging.WARNING
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_sound_plays_paplay(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def _which(name: str) -> str | None:
        if name == "paplay":
            return "/usr/bin/paplay"
        return None

    def _run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("infrastructure.adapters.popen_alert_sound.which", _which)
    monkeypatch.setattr(
        "infrastructure.adapters.popen_alert_sound.subprocess.run",
        _run,
    )
    PopenAlertSound().play_new_alert()
    assert commands[0][0] == "/usr/bin/paplay"
    assert "--volume=18000" in commands[0]


def test_sound_plays_aplay_without_volume(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def _which(name: str) -> str | None:
        if name == "aplay":
            return "/usr/bin/aplay"
        return None

    def _run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("infrastructure.adapters.popen_alert_sound.which", _which)
    monkeypatch.setattr(
        "infrastructure.adapters.popen_alert_sound.subprocess.run",
        _run,
    )
    PopenAlertSound().play_new_alert()
    assert commands[0] == ["/usr/bin/aplay", commands[0][1]]
    assert commands[0][1].endswith(".wav")
    assert not Path(commands[0][1]).exists()


def _sound_logger() -> logging.Logger:
    return logging.getLogger("infrastructure.adapters.popen_alert_sound")


def _has_sound_failed(caplog: pytest.LogCaptureFixture) -> bool:
    return any(
        getattr(record, "semantic", {}).get("event") == POLL_SOUND_FAILED
        for record in caplog.records
        if hasattr(record, "semantic")
    )


def test_sound_play_error_fail_open(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "infrastructure.adapters.popen_alert_sound.which",
        lambda name: "/usr/bin/paplay" if name == "paplay" else None,
    )

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("no device")

    monkeypatch.setattr(
        "infrastructure.adapters.popen_alert_sound.subprocess.run",
        _boom,
    )
    sound_logger = _sound_logger()
    previous = sound_logger.level
    sound_logger.setLevel(logging.DEBUG)
    try:
        with caplog.at_level("DEBUG"):
            PopenAlertSound().play_new_alert()
    finally:
        sound_logger.setLevel(previous)
    assert _has_sound_failed(caplog)


def test_sound_play_error_without_debug(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "infrastructure.adapters.popen_alert_sound.which",
        lambda name: "/usr/bin/paplay" if name == "paplay" else None,
    )

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("no device")

    monkeypatch.setattr(
        "infrastructure.adapters.popen_alert_sound.subprocess.run",
        _boom,
    )
    sound_logger = _sound_logger()
    previous = sound_logger.level
    sound_logger.setLevel(logging.WARNING)
    try:
        with caplog.at_level("WARNING"):
            PopenAlertSound().play_new_alert()
    finally:
        sound_logger.setLevel(previous)
    assert _has_sound_failed(caplog)


def test_sound_tempfile_error_fail_open(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "infrastructure.adapters.popen_alert_sound.which",
        lambda name: "/usr/bin/paplay" if name == "paplay" else None,
    )

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk")

    monkeypatch.setattr(
        "infrastructure.adapters.popen_alert_sound.tempfile.NamedTemporaryFile",
        _fail,
    )
    with caplog.at_level("WARNING"):
        PopenAlertSound().play_new_alert()
    assert _has_sound_failed(caplog)
