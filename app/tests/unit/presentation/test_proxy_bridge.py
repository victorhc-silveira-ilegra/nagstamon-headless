from __future__ import annotations

import socket
import threading
import time
from datetime import time as dt_time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.config.settings import Settings
from presentation.cli.proxy_bridge import (
    ProxyBridgeServer,
    build_parser,
    build_server,
    forward_stream,
    main,
    parse_upstream_proxy,
    run,
)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        servers_dir=tmp_path,
        proxy_addr="http://10.150.8.18:3128",
        refresh_interval=1,
        http_timeout_seconds=2.0,
        http_max_workers=2,
        log_level="INFO",
        log_format="text",
        log_file=None,
        log_dir=None,
        dedup_enabled=True,
        dedup_window_minutes=30,
        filter_window_enabled=True,
        filter_window_start=dt_time(13, 30),
        filter_window_end=dt_time(18, 0),
        filter_window_allow_past_active_alerts=False,
        filter_timezone="America/Sao_Paulo",
        filter_weekdays=(0, 1, 2, 3, 4),
        filter_hold_fast_seconds=600,
        filter_hold_critical_seconds=900,
        filter_hold_warning_seconds=1200,
        filter_duration_max_seconds=86400,
        sound_enabled=False,
        gchat_webhook_url="",
        dedup_ledger_path=None,
        proxy_bridge_host="127.0.0.1",
        proxy_bridge_port=0,
    )


def test_parse_upstream_proxy() -> None:
    assert parse_upstream_proxy("") == ("", 0)
    assert parse_upstream_proxy("http://proxy.local:3128") == ("proxy.local", 3128)
    assert parse_upstream_proxy("https://secure.proxy:8443") == ("secure.proxy", 8443)
    assert parse_upstream_proxy("proxy.local:3128") == ("proxy.local", 3128)
    assert parse_upstream_proxy("proxy.local") == ("proxy.local", 3128)
    assert parse_upstream_proxy("https://secure.proxy") == ("secure.proxy", 443)


def test_forward_stream() -> None:
    src, dst = socket.socketpair()
    try:
        t = threading.Thread(target=forward_stream, args=(src, dst), daemon=True)
        t.start()
        src.sendall(b"hello world")
        src.close()
        t.join(timeout=1.0)
        received = dst.recv(1024)
        assert received == b"hello world"
    finally:
        dst.close()


def test_proxy_bridge_server_handle_client_invalid(tmp_path: Path) -> None:
    server = ProxyBridgeServer("127.0.0.1", 0, "127.0.0.1", 3128, timeout=0.5)
    c1, c2 = socket.socketpair()
    try:
        c1.close()
        server.handle_client(c2)
    finally:
        c2.close()

    c3, c4 = socket.socketpair()
    try:
        c3.sendall(b"GET / HTTP/1.1\r\n\r\n")
        server.handle_client(c4)
    finally:
        c3.close()
        c4.close()


def test_proxy_bridge_server_full_tunnel(tmp_path: Path) -> None:
    upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upstream_sock.bind(("127.0.0.1", 0))
    upstream_sock.listen(1)
    up_port = upstream_sock.getsockname()[1]

    def upstream_handler() -> None:
        conn, _ = upstream_sock.accept()
        data = conn.recv(1024)
        assert b"CONNECT" in data
        conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        msg = conn.recv(1024)
        assert msg == b"ping from client"
        conn.sendall(b"pong from upstream")
        conn.close()

    up_thread = threading.Thread(target=upstream_handler, daemon=True)
    up_thread.start()

    server = ProxyBridgeServer("127.0.0.1", 0, "127.0.0.1", up_port, timeout=2.0)
    server.start()
    port = server.listen_port
    assert port > 0

    stop_event = threading.Event()
    serve_thread = threading.Thread(
        target=server.serve_forever, args=(stop_event,), daemon=True
    )
    serve_thread.start()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))
    client.sendall(b"CONNECT localhost:443 HTTP/1.1\r\n\r\n")
    resp = client.recv(1024)
    assert b"200 Connection established" in resp

    client.sendall(b"ping from client")
    reply = client.recv(1024)
    assert reply == b"pong from upstream"
    client.close()

    stop_event.set()
    server.stop()
    serve_thread.join(timeout=1.0)
    upstream_sock.close()
    up_thread.join(timeout=1.0)


def test_proxy_bridge_server_upstream_error() -> None:
    upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upstream_sock.bind(("127.0.0.1", 0))
    upstream_sock.listen(1)
    up_port = upstream_sock.getsockname()[1]

    def upstream_handler() -> None:
        conn, _ = upstream_sock.accept()
        _ = conn.recv(1024)
        conn.sendall(b"HTTP/1.1 503 Service Unavailable\r\n\r\n")
        conn.close()

    up_thread = threading.Thread(target=upstream_handler, daemon=True)
    up_thread.start()

    server = ProxyBridgeServer("127.0.0.1", 0, "127.0.0.1", up_port, timeout=1.0)
    c1, c2 = socket.socketpair()
    try:
        c1.sendall(b"CONNECT localhost:invalid_port HTTP/1.1\r\n\r\n")
        server.handle_client(c2)
    finally:
        c1.close()
        c2.close()
        upstream_sock.close()
        up_thread.join(timeout=1.0)


def test_proxy_bridge_server_dns_fail() -> None:
    server = ProxyBridgeServer("127.0.0.1", 0, "127.0.0.1", 1, timeout=0.5)
    c1, c2 = socket.socketpair()
    try:
        with patch("socket.gethostbyname", side_effect=socket.gaierror("fail")):
            c1.sendall(b"CONNECT invalid.nonexistent.domain:443 HTTP/1.1\r\n\r\n")
            server.handle_client(c2)
    finally:
        c1.close()
        c2.close()


def test_build_server(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    server = build_server(settings, listen_host="127.0.0.2", listen_port=9999)
    assert server._listen_host == "127.0.0.2"
    assert server._listen_port == 9999


def test_build_parser() -> None:
    parser = build_parser()
    args = parser.parse_args(["--listen-host", "127.0.0.1", "--listen-port", "3128"])
    assert args.listen_host == "127.0.0.1"
    assert args.listen_port == 3128


def test_run_success(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    stop_event = threading.Event()
    stop_event.set()
    exit_code = run(
        settings=settings,
        stop_event=stop_event,
        args=["--listen-port", "0"],
    )
    assert exit_code == 0


def test_run_keyboard_interrupt(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with patch.object(
        ProxyBridgeServer, "serve_forever", side_effect=KeyboardInterrupt
    ):
        exit_code = run(settings=settings, args=["--listen-port", "0"])
        assert exit_code == 0


def test_run_server_error(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with patch.object(
        ProxyBridgeServer, "serve_forever", side_effect=RuntimeError("boom")
    ):
        exit_code = run(settings=settings, args=["--listen-port", "0"])
        assert exit_code == 1


def test_run_setup_error() -> None:
    with patch(
        "presentation.cli.proxy_bridge.Settings.from_env",
        side_effect=ValueError("bad"),
    ):
        exit_code = run(settings=None, args=[])
        assert exit_code == 1


def test_main() -> None:
    with (
        patch("presentation.cli.proxy_bridge.run", return_value=0),
        pytest.raises(SystemExit) as exc,
    ):
        main()
    assert exc.value.code == 0


def test_serve_forever_auto_start() -> None:
    server = ProxyBridgeServer("127.0.0.1", 0, "127.0.0.1", 3128)
    stop_event = threading.Event()
    stop_event.set()
    server.serve_forever(stop_event)
    server.stop()


def test_forward_stream_oserror() -> None:
    mock_src = MagicMock()
    mock_src.recv.side_effect = OSError("network error")
    mock_dst = MagicMock()
    forward_stream(mock_src, mock_dst)


def test_stop_socket_close_error() -> None:
    server = ProxyBridgeServer("127.0.0.1", 0, "127.0.0.1", 3128)
    server.start()
    mock_sock = MagicMock()
    mock_sock.close.side_effect = OSError("close fail")
    server._server_sock = mock_sock
    server.stop()
    assert server._server_sock is None


def test_serve_forever_timeout_loop() -> None:
    server = ProxyBridgeServer("127.0.0.1", 0, "127.0.0.1", 3128)
    server.start()
    assert server._server_sock is not None
    server._server_sock.settimeout(0.05)
    stop_event = threading.Event()
    t = threading.Thread(target=server.serve_forever, args=(stop_event,), daemon=True)
    t.start()
    time.sleep(0.12)
    stop_event.set()
    server.stop()
    t.join(timeout=1.0)


def test_handle_client_upstream_empty_response() -> None:
    server = ProxyBridgeServer("127.0.0.1", 0, "127.0.0.1", 3128)
    mock_client = MagicMock()
    mock_client.recv.return_value = b"CONNECT host:443 HTTP/1.1\r\n\r\n"
    mock_upstream = MagicMock()
    mock_upstream.recv.return_value = b""
    with (
        patch("socket.create_connection", return_value=mock_upstream),
        patch("socket.gethostbyname", return_value="127.0.0.1"),
    ):
        server.handle_client(mock_client)
    mock_upstream.close.assert_called()
