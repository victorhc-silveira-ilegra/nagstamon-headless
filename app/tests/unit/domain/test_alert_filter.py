from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from domain.entities.alert import Alert
from domain.entities.errors import DomainValidationError
from domain.entities.monitor_server import MonitorServer
from domain.entities.severity import Severity
from domain.services.alert_filter import AlertFilterPolicy, parse_duration_seconds

NOW = datetime(2026, 8, 13, 17, 0, 0, tzinfo=UTC)


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
    other_host = _alert(host="db02")
    assert first.dedup_key() == second.dedup_key()
    assert first.dedup_key() == "prod\0DiskFull\0db01\0\0disk is full"
    assert other.dedup_key() != first.dedup_key()
    assert other_host.dedup_key() != first.dedup_key()


def test_filter_status_info() -> None:
    policy = AlertFilterPolicy()
    assert policy.is_filtered(_alert(status_text="Connection timeout on host"), NOW)
    assert policy.is_filtered(
        _alert(status_text="", alertname="X", desc="Unknown error from probe"),
        NOW,
    )


def test_parse_duration_seconds() -> None:
    assert parse_duration_seconds("1d 0h 0m") == 86400
    assert parse_duration_seconds("0d 0h 9m") == 540
    assert parse_duration_seconds("0d 0h 10m") == 600
    assert parse_duration_seconds("0d 23h 0m") == 82800
    assert parse_duration_seconds("0d, 2h, 15m, 3s") == 8103
    assert parse_duration_seconds("") is None
    assert parse_duration_seconds("x 10x 1 ah") is None
    assert parse_duration_seconds("2h") == 7200


def test_filter_duration_from_python_clock_or_parsed_string() -> None:
    policy = AlertFilterPolicy()
    assert policy.is_filtered(_alert(duration_str="1d 0h 0m"), NOW)
    assert policy.is_filtered(
        _alert(
            alertname="CPU",
            desc="cpu high",
            status_text="cpu",
            duration_str="0d 0h 9m",
        ),
        NOW,
    )
    assert not policy.is_filtered(
        _alert(
            alertname="CPU",
            desc="cpu high",
            status_text="cpu",
            duration_str="0d 0h 10m",
        ),
        NOW,
    )
    assert not policy.is_filtered(_alert(duration_str="0d 0h 3m"), NOW)
    assert policy.is_filtered(_alert(duration_str="0d 0h 2m"), NOW)
    assert policy.is_filtered(_alert(duration_str="nope"), NOW)
    clock_wins = _alert(
        alertname="CPU",
        desc="cpu high",
        status_text="cpu",
        starts_at=NOW - timedelta(minutes=9),
        duration_str="0d 0h 10m",
    )
    assert policy.is_filtered(clock_wins, NOW)
    ignore_string = _alert(
        starts_at=NOW - timedelta(minutes=30),
        duration_str="1d 0h 0m",
    )
    assert not policy.is_filtered(ignore_string, NOW)


def test_filter_starts_at_windows() -> None:
    policy = AlertFilterPolicy()
    too_new = _alert(starts_at=NOW - timedelta(seconds=60))
    too_old = _alert(starts_at=NOW - timedelta(days=1))
    ok = _alert(starts_at=NOW - timedelta(minutes=30))
    naive = _alert(starts_at=datetime(2026, 8, 13, 16, 30, 0))
    naive_now = datetime(2026, 8, 13, 17, 0, 0)
    assert policy.is_filtered(too_new, NOW)
    assert policy.is_filtered(too_old, NOW)
    assert not policy.is_filtered(ok, NOW)
    assert not policy.is_filtered(naive, naive_now)


def test_filter_numeric_duration_hold_and_one_day() -> None:
    policy = AlertFilterPolicy()
    cpu = dict(alertname="CPU", desc="cpu high", status_text="cpu")
    nine_min = _alert(starts_at=NOW - timedelta(minutes=9), **cpu)
    ten_min = _alert(starts_at=NOW - timedelta(minutes=10), **cpu)
    two_min = _alert(starts_at=NOW - timedelta(minutes=2))
    three_min = _alert(starts_at=NOW - timedelta(minutes=3))
    one_day = _alert(starts_at=NOW - timedelta(seconds=86400))
    assert policy.is_filtered(nine_min, NOW)
    assert not policy.is_filtered(ten_min, NOW)
    assert policy.is_filtered(two_min, NOW)
    assert not policy.is_filtered(three_min, NOW)
    assert policy.is_filtered(one_day, NOW)


def test_filter_daily_window_for_now() -> None:
    policy = AlertFilterPolicy()
    keep = _alert(starts_at=NOW - timedelta(minutes=30))
    started = datetime(2026, 8, 13, 16, 30, 0, tzinfo=UTC)
    before = datetime(2026, 8, 13, 16, 29, 0, tzinfo=UTC)
    end = datetime(2026, 8, 13, 21, 0, 0, tzinfo=UTC)
    after = datetime(2026, 8, 13, 21, 0, 1, tzinfo=UTC)
    early = _alert(starts_at=started)
    assert policy.is_filtered(early, before)
    assert not policy.is_filtered(keep, end)
    assert policy.is_filtered(early, after)


def test_filter_start_must_fall_in_window_today() -> None:
    policy = AlertFilterPolicy()
    early_today = _alert(starts_at=datetime(2026, 8, 13, 16, 29, 0, tzinfo=UTC))
    in_window = _alert(starts_at=datetime(2026, 8, 13, 16, 30, 0, tzinfo=UTC))
    later_now = datetime(2026, 8, 13, 18, 0, 0, tzinfo=UTC)
    yesterday_in_clock = _alert(starts_at=datetime(2026, 8, 12, 18, 30, 0, tzinfo=UTC))
    two_days = _alert(starts_at=later_now - timedelta(days=2))
    assert policy.is_filtered(early_today, later_now)
    assert not policy.is_filtered(in_window, later_now)
    assert policy.is_filtered(yesterday_in_clock, later_now)
    assert policy.is_filtered(two_days, later_now)


def test_filter_acknowledged() -> None:
    policy = AlertFilterPolicy()
    open_alert = _alert(starts_at=NOW - timedelta(minutes=30))
    assert policy.is_filtered(
        _alert(acknowledged=True, starts_at=open_alert.starts_at), NOW
    )
    assert not policy.is_filtered(open_alert, NOW)


def test_filter_alertmanager_noise_and_silence() -> None:
    policy = AlertFilterPolicy()
    assert policy.is_filtered(_alert(alertname="Watchdog"), NOW)
    assert policy.is_filtered(_alert(alertname="InfoInhibitor"), NOW)
    assert policy.is_filtered(_alert(alert_state="pending"), NOW)
    assert policy.is_filtered(_alert(silenced_by=("s1",)), NOW)
    assert policy.is_filtered(_alert(inhibited_by=("i1",)), NOW)


def test_filter_custom_window_and_timezone() -> None:
    policy = AlertFilterPolicy(
        window_start=time(10, 0),
        window_end=time(11, 0),
        timezone=ZoneInfo("UTC"),
    )
    inside = datetime(2026, 8, 13, 10, 5, 0, tzinfo=UTC)
    outside = datetime(2026, 8, 13, 11, 0, 1, tzinfo=UTC)
    started = datetime(2026, 8, 13, 10, 0, 0, tzinfo=UTC)
    keep = _alert(starts_at=started)
    assert not policy.is_filtered(keep, inside)
    assert policy.is_filtered(keep, outside)


def test_filter_custom_duration_bounds() -> None:
    policy = AlertFilterPolicy(
        hold_fast_seconds=60,
        hold_critical_seconds=60,
        hold_warning_seconds=60,
        max_duration_seconds=3600,
    )
    nine_min = _alert(starts_at=NOW - timedelta(minutes=9))
    two_hours = _alert(starts_at=NOW - timedelta(hours=2))
    assert not policy.is_filtered(nine_min, NOW)
    assert policy.is_filtered(two_hours, NOW)


def test_apply_keeps_effective_alerts() -> None:
    policy = AlertFilterPolicy()
    noise = _alert(alertname="Watchdog")
    keep = _alert(starts_at=NOW - timedelta(minutes=30))
    result = policy.apply([noise, keep], NOW)
    assert result == [keep]


def test_filter_started_before_daemon_boot() -> None:
    boot = NOW - timedelta(minutes=15)
    policy = AlertFilterPolicy(not_before=boot)
    already_open = _alert(starts_at=NOW - timedelta(minutes=30))
    after_boot = _alert(starts_at=NOW - timedelta(minutes=12))
    at_boot = _alert(starts_at=boot)
    cgi_old = _alert(duration_str="0d 0h 20m")
    cgi_unknown = _alert()
    naive_boot = datetime(2026, 8, 13, 16, 55, 0)
    naive_policy = AlertFilterPolicy(not_before=naive_boot)
    naive_old = _alert(starts_at=datetime(2026, 8, 13, 16, 30, 0))
    assert policy.is_filtered(already_open, NOW)
    assert not policy.is_filtered(after_boot, NOW)
    assert not policy.is_filtered(at_boot, NOW)
    assert policy.is_filtered(cgi_old, NOW)
    assert policy.is_filtered(cgi_unknown, NOW)
    assert naive_policy.is_filtered(naive_old, NOW)


def test_filter_hold_classes_and_missing_start() -> None:
    policy = AlertFilterPolicy()
    info = _alert(
        severity=Severity("info"),
        starts_at=NOW - timedelta(minutes=30),
    )
    generic = _alert(
        alertname="HttpError",
        desc="status 500",
        status_text="500",
        starts_at=NOW - timedelta(minutes=9),
    )
    generic_ok = _alert(
        alertname="HttpError",
        desc="status 500",
        status_text="500",
        starts_at=NOW - timedelta(minutes=10),
    )
    high_load = dict(alertname="HighLoad", desc="load average", status_text="load")
    high_load_early = _alert(starts_at=NOW - timedelta(minutes=9), **high_load)
    high_load_ok = _alert(starts_at=NOW - timedelta(minutes=10), **high_load)
    critical = _alert(
        alertname="HttpError",
        desc="status 500",
        status_text="500",
        severity=Severity("critical"),
        starts_at=NOW - timedelta(minutes=3),
    )
    critical_early = _alert(
        alertname="HttpError",
        desc="status 500",
        status_text="500",
        severity=Severity("critical"),
        starts_at=NOW - timedelta(minutes=2),
    )
    down = _alert(
        alertname="DOWN",
        desc="host is down",
        status_text="DOWN",
        severity=Severity("warning"),
        starts_at=NOW - timedelta(minutes=3),
    )
    pix_host = _alert(
        alertname="HttpError",
        desc="status 500",
        status_text="500",
        host="spi-auto-pix-messenger-764b485446-s2xpx",
        starts_at=NOW - timedelta(minutes=3),
    )
    assert policy.is_filtered(info, NOW)
    assert policy.is_filtered(generic, NOW)
    assert not policy.is_filtered(generic_ok, NOW)
    assert policy.is_filtered(high_load_early, NOW)
    assert not policy.is_filtered(high_load_ok, NOW)
    assert policy.is_filtered(critical_early, NOW)
    assert not policy.is_filtered(critical, NOW)
    assert not policy.is_filtered(down, NOW)
    assert policy.is_filtered(pix_host, NOW)
    assert policy.is_filtered(_alert(), NOW)
