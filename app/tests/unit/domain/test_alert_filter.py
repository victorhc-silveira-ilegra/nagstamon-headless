from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from domain.entities.alert import Alert
from domain.entities.errors import DomainValidationError
from domain.entities.monitor_server import MonitorServer
from domain.entities.severity import Severity
from domain.services.alert_filter import AlertFilterPolicy

NOW = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)


def _alert(**overrides: object) -> Alert:
    payload: dict[str, object] = {
        "server": "prod",
        "severity": Severity("warning"),
        "alertname": "DiskFull",
        "app": "db01",
        "desc": "disk is full",
        "status_text": "DiskFull disk is full",
    }
    payload.update(overrides)
    return Alert(**payload)  # type: ignore[arg-type]


def test_severity_normalizes_and_rejects_empty() -> None:
    assert Severity(" critical ").value == "CRITICAL"
    with pytest.raises(DomainValidationError, match="severity"):
        Severity("   ")


def test_monitor_server_validation_and_alertmanager_detection() -> None:
    server = MonitorServer(
        name=" server_am ",
        url=" http://am.example/ ",
        proxy=" http://proxy:3128 ",
        username=" user ",
        password="secret",
        server_type=" Prometheus-Alertmanager ",
    )
    assert server.name == "server_am"
    assert server.url == "http://am.example/"
    assert server.proxy == "http://proxy:3128"
    assert server.username == "user"
    assert server.password == "secret"
    assert server.server_type == "prometheus-alertmanager"
    assert server.is_alertmanager is True
    named = MonitorServer(
        name="alertmanager-prod",
        url="http://am.example",
        proxy="",
        username="",
        password="",
        server_type="other",
    )
    assert named.is_alertmanager is True
    nagios = MonitorServer(
        name="core",
        url="http://nagios.example",
        proxy="",
        username="",
        password="",
        server_type="nagios",
    )
    assert nagios.is_alertmanager is False
    with pytest.raises(DomainValidationError, match="name"):
        MonitorServer(
            name=" ",
            url="http://x",
            proxy="",
            username="",
            password="",
            server_type="",
        )
    with pytest.raises(DomainValidationError, match="url"):
        MonitorServer(
            name="core",
            url=" ",
            proxy="",
            username="",
            password="",
            server_type="",
        )


def test_alert_validation() -> None:
    alert = _alert(desc="  space  ", status_text="  txt  ", alert_state=" SUPPRESSED ")
    assert alert.desc == "space"
    assert alert.status_text == "txt"
    assert alert.alert_state == "suppressed"
    with pytest.raises(DomainValidationError, match="server"):
        _alert(server=" ")
    with pytest.raises(DomainValidationError, match="alertname"):
        _alert(alertname=" ")
    with pytest.raises(DomainValidationError, match="app"):
        _alert(app=" ")


def test_alert_dedup_key_stable_and_ignores_starts_at() -> None:
    first = _alert(desc="  disk is full  ", starts_at=NOW)
    second = _alert(starts_at=None)
    other = _alert(alertname="CPU")
    assert first.dedup_key() == second.dedup_key()
    assert first.dedup_key() == "prod\0DiskFull\0db01\0disk is full"
    assert other.dedup_key() != first.dedup_key()


def test_filter_status_info_and_duration_string() -> None:
    policy = AlertFilterPolicy()
    assert policy.is_filtered(_alert(status_text="Connection timeout on host"), NOW)
    assert policy.is_filtered(
        _alert(status_text="", alertname="X", desc="Unknown error from probe"),
        NOW,
    )
    assert policy.is_filtered(_alert(duration_str="3d 0h 0m"), NOW)
    assert policy.is_filtered(_alert(duration_str="0d 0h 3m"), NOW)
    assert not policy.is_filtered(_alert(duration_str="0d 1h 0m"), NOW)


def test_filter_starts_at_windows() -> None:
    policy = AlertFilterPolicy()
    too_new = _alert(starts_at=NOW - timedelta(seconds=60))
    too_old = _alert(starts_at=NOW - timedelta(days=3))
    ok = _alert(starts_at=NOW - timedelta(minutes=30))
    naive = _alert(starts_at=datetime(2026, 8, 13, 11, 0, 0))
    naive_now = datetime(2026, 8, 13, 12, 0, 0)
    assert policy.is_filtered(too_new, NOW)
    assert policy.is_filtered(too_old, NOW)
    assert not policy.is_filtered(ok, NOW)
    assert not policy.is_filtered(naive, naive_now)


def test_filter_alertmanager_noise_and_silence() -> None:
    policy = AlertFilterPolicy()
    assert policy.is_filtered(_alert(alertname="Watchdog"), NOW)
    assert policy.is_filtered(_alert(alertname="InfoInhibitor"), NOW)
    assert policy.is_filtered(_alert(alert_state="pending"), NOW)
    assert policy.is_filtered(_alert(silenced_by=("s1",)), NOW)
    assert policy.is_filtered(_alert(inhibited_by=("i1",)), NOW)


def test_apply_keeps_effective_alerts() -> None:
    policy = AlertFilterPolicy()
    noise = _alert(alertname="Watchdog")
    keep = _alert(starts_at=NOW - timedelta(hours=2))
    result = policy.apply([noise, keep], NOW)
    assert result == [keep]
