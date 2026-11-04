from __future__ import annotations

import argparse
import contextlib
import logging
import socket
import sys
import threading
from urllib.parse import urlsplit

from infrastructure.config.settings import Settings
from infrastructure.logging import (
    PROXY_BRIDGE_FAILED,
    PROXY_BRIDGE_STARTED,
    log_event,
)
from presentation.logging import setup_logging

logger = logging.getLogger(__name__)


def parse_upstream_proxy(proxy_addr: str) -> tuple[str, int]:
    clean = proxy_addr.strip()
    if not clean:
        return "", 0
    if "://" not in clean:
        clean = f"http://{clean}"
    parts = urlsplit(clean)
    host = parts.hostname or ""
    port = parts.port or (443 if parts.scheme == "https" else 3128)
    return host, port


def forward_stream(src: socket.socket, dst: socket.socket) -> None:
    with contextlib.suppress(OSError):
        while True:
            data = src.recv(32768)
            if not data:
                break
            dst.sendall(data)


class ProxyBridgeServer:
    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        upstream_host: str,
        upstream_port: int,
        timeout: float = 10.0,
    ) -> None:
        self._listen_host = listen_host
        self._listen_port = listen_port
        self._upstream_host = upstream_host
        self._upstream_port = upstream_port
        self._timeout = timeout
        self._server_sock: socket.socket | None = None
        self._stop_event = threading.Event()

    @property
    def listen_port(self) -> int:
        return self._listen_port

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self._listen_host, self._listen_port))
        self._listen_port = sock.getsockname()[1]
        sock.listen(100)
        sock.settimeout(0.5)
        self._server_sock = sock

    def stop(self) -> None:
        self._stop_event.set()
        if self._server_sock is not None:
            with contextlib.suppress(Exception):
                self._server_sock.close()
            self._server_sock = None

    def handle_client(self, client_sock: socket.socket) -> None:
        upstream: socket.socket | None = None
        try:
            with contextlib.suppress(Exception):
                client_sock.settimeout(self._timeout)
                req = b""
                while b"\r\n\r\n" not in req:
                    chunk = client_sock.recv(4096)
                    if not chunk:
                        return
                    req += chunk
                header_text = req.decode("latin1")
                first_line = header_text.split("\r\n")[0]
                parts = first_line.split()
                if len(parts) < 2 or parts[0] != "CONNECT":
                    return
                target = parts[1]
                host, port_str = (
                    target.split(":", 1) if ":" in target else (target, "443")
                )
                try:
                    port = int(port_str)
                except ValueError:
                    port = 443
                try:
                    ip = socket.gethostbyname(host)
                except Exception:
                    ip = host
                upstream = socket.create_connection(
                    (self._upstream_host, self._upstream_port),
                    timeout=self._timeout,
                )
                connect_cmd = (
                    f"CONNECT {ip}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
                )
                upstream.sendall(connect_cmd.encode("latin1"))
                resp = b""
                while b"\r\n\r\n" not in resp:
                    chunk = upstream.recv(4096)
                    if not chunk:
                        return
                    resp += chunk
                if b"200 Connection established" not in resp and b"200 OK" not in resp:
                    return
                client_sock.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                client_sock.settimeout(None)
                upstream.settimeout(None)
                t1 = threading.Thread(
                    target=forward_stream, args=(client_sock, upstream), daemon=True
                )
                t2 = threading.Thread(
                    target=forward_stream, args=(upstream, client_sock), daemon=True
                )
                t1.start()
                t2.start()
                t1.join()
                t2.join()
        finally:
            client_sock.close()
            if upstream is not None:
                upstream.close()

    def serve_forever(self, stop_event: threading.Event | None = None) -> None:
        active_stop = stop_event or self._stop_event
        if self._server_sock is None:
            self.start()
        assert self._server_sock is not None
        while not active_stop.is_set():
            try:
                client_sock, _ = self._server_sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            t = threading.Thread(
                target=self.handle_client,
                args=(client_sock,),
                daemon=True,
            )
            t.start()


def build_server(
    settings: Settings,
    *,
    listen_host: str | None = None,
    listen_port: int | None = None,
) -> ProxyBridgeServer:
    host = listen_host or settings.proxy_bridge_host
    port = listen_port or settings.proxy_bridge_port
    up_host, up_port = parse_upstream_proxy(settings.proxy_addr)
    return ProxyBridgeServer(
        listen_host=host,
        listen_port=port,
        upstream_host=up_host,
        upstream_port=up_port,
        timeout=settings.http_timeout_seconds,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nagstamon-headless-proxy",
        description="Proxy bridge local com resolucao de DNS para Squid",
    )
    parser.add_argument("--listen-host", default=None)
    parser.add_argument("--listen-port", type=int, default=None)
    return parser


def run(
    *,
    settings: Settings | None = None,
    stop_event: threading.Event | None = None,
    args: list[str] | None = None,
) -> int:
    try:
        resolved = settings or Settings.from_env()
        setup_logging(
            level=resolved.log_level,
            log_format=resolved.log_format,
            log_file=resolved.log_file,
        )
        cli_args = sys.argv[1:] if args is None else args
        parsed = build_parser().parse_args(cli_args)
        server = build_server(
            resolved,
            listen_host=parsed.listen_host,
            listen_port=parsed.listen_port,
        )
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            PROXY_BRIDGE_FAILED,
            error_type=type(exc).__name__,
        )
        return 1
    log_event(
        logger,
        logging.INFO,
        PROXY_BRIDGE_STARTED,
        listen_host=parsed.listen_host or resolved.proxy_bridge_host,
        listen_port=parsed.listen_port or resolved.proxy_bridge_port,
        upstream_proxy=resolved.proxy_addr,
    )
    try:
        server.serve_forever(stop_event)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            PROXY_BRIDGE_FAILED,
            error_type=type(exc).__name__,
        )
        return 1
    finally:
        server.stop()
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
