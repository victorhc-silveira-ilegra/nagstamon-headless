from __future__ import annotations

from domain.entities.alert import Alert
from domain.entities.severity import Severity
from domain.services.alert_hold import (
    HOLD_CRITICAL_SECONDS,
    HOLD_FAST_SECONDS,
    HOLD_WARNING_SECONDS,
    hold_seconds,
)


def _alert(**overrides: object) -> Alert:
    payload: dict[str, object] = {
        "server": "prod",
        "severity": Severity("warning"),
        "alertname": "HttpError",
        "app": "api",
        "desc": "status 500",
        "status_text": "500",
    }
    payload.update(overrides)
    return Alert(**payload)  # type: ignore[arg-type]


def test_hold_info_never_pages() -> None:
    assert hold_seconds(_alert(severity=Severity("info"), alertname="DiskFull")) is None


def test_hold_fast_disk_and_down() -> None:
    assert hold_seconds(_alert(alertname="DiskFull", desc="disk is full")) == (
        HOLD_FAST_SECONDS
    )
    assert hold_seconds(_alert(alertname="DiskSpace", desc="usage 95 percent")) == (
        HOLD_FAST_SECONDS
    )
    assert hold_seconds(_alert(alertname="DOWN", desc="host is down")) == (
        HOLD_FAST_SECONDS
    )
    assert hold_seconds(_alert(alertname="TLSExpire", desc="certificate expired")) == (
        HOLD_FAST_SECONDS
    )
    assert hold_seconds(
        _alert(alertname="Certificado", desc="certificado expirado")
    ) == (HOLD_FAST_SECONDS)
    assert hold_seconds(
        _alert(alertname="LoginFail", desc="login endpoint failed")
    ) == (HOLD_FAST_SECONDS)


def test_hold_transient_overrides_critical() -> None:
    cpu = _alert(
        severity=Severity("critical"),
        alertname="CPUThrottlingHigh",
        desc="cpu throttling",
    )
    assert hold_seconds(cpu) == HOLD_WARNING_SECONDS
    assert hold_seconds(_alert(alertname="HighLoad")) == HOLD_WARNING_SECONDS
    assert hold_seconds(_alert(alertname="NodeLoadHigh")) == HOLD_WARNING_SECONDS
    assert hold_seconds(_alert(alertname="MemoriaAlta", desc="memoria")) == (
        HOLD_WARNING_SECONDS
    )


def test_hold_download_is_not_transient_load() -> None:
    alert = _alert(severity=Severity("critical"), alertname="DownloadFailed")
    assert hold_seconds(alert) == HOLD_CRITICAL_SECONDS


def test_hold_severity_defaults() -> None:
    assert hold_seconds(_alert(severity=Severity("critical"))) == HOLD_CRITICAL_SECONDS
    assert hold_seconds(_alert()) == HOLD_WARNING_SECONDS


def test_hold_pix_in_host_is_not_fast() -> None:
    alert = _alert(host="spi-auto-pix-messenger-764b485446-s2xpx")
    assert hold_seconds(alert) == HOLD_WARNING_SECONDS
