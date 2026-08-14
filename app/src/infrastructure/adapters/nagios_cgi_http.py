from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from urllib.parse import unquote

import httpx

from domain.entities.alert import Alert
from domain.entities.monitor_server import MonitorServer
from domain.entities.severity import Severity
from infrastructure.adapters.http_client import build_http_client, log_fetch_failed

CGI_SUFFIX = "/cgi-bin/status.cgi?host=all&servicestatustypes=253&limit=0"
DURATION_RE = re.compile(r"(\d+d\s+\d+h\s+\d+m(?:\s+\d+s)?)", re.IGNORECASE)
STATUS_CLASS_RE = re.compile(r"^status(CRITICAL|WARNING)(ACK)?$", re.IGNORECASE)


def _query_param(html: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}=([^&\"'\s>]+)", html, re.IGNORECASE)
    if not match:
        return ""
    return unquote(match.group(1).replace("+", " ")).strip()


def _severity_from_class(classes: str) -> tuple[str | None, bool]:
    found: str | None = None
    ack = False
    for token in classes.split():
        match = STATUS_CLASS_RE.match(token)
        if match:
            found = match.group(1).upper()
            ack = match.group(2) is not None
    return found, ack


class _Td:
    def __init__(self, classes: str) -> None:
        self.classes = classes
        self.parts: list[str] = []
        self.hrefs: list[str] = []

    @property
    def text(self) -> str:
        return " ".join(part.strip() for part in self.parts if part.strip())


class _NagiosHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[_Td]] = []
        self._tr_stack: list[list[_Td]] = []
        self._td_stack: list[_Td] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = {key: (value or "") for key, value in attrs}
        if tag == "tr":
            self._tr_stack.append([])
        elif tag == "td" and self._tr_stack:
            self._td_stack.append(_Td(mapping.get("class", "")))
        elif tag == "a" and self._td_stack:
            href = mapping.get("href", "")
            if href:
                for cell in self._td_stack:
                    cell.hrefs.append(href)
        elif tag == "img" and self._td_stack:
            alt = mapping.get("alt") or mapping.get("title") or ""
            if alt:
                for cell in self._td_stack:
                    cell.parts.append(alt)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._td_stack:
            cell = self._td_stack.pop()
            if self._tr_stack:
                self._tr_stack[-1].append(cell)
        elif tag == "tr" and self._tr_stack:
            row = self._tr_stack.pop()
            if row:
                self.rows.append(row)

    def handle_data(self, data: str) -> None:
        for cell in self._td_stack:
            cell.parts.append(data)


def _alerts_from_html(server: MonitorServer, html: str) -> list[Alert]:
    parser = _NagiosHtmlParser()
    parser.feed(html)
    parser.close()
    alerts: list[Alert] = []
    last_host = ""
    for row in parser.rows:
        severity: str | None = None
        ack = False
        for cell in row:
            sev, cell_ack = _severity_from_class(cell.classes)
            if sev is not None:
                severity = sev
                ack = ack or cell_ack
        if severity is None:
            continue
        blob = " ".join(cell.text for cell in row)
        href_blob = " ".join(href for cell in row for href in cell.hrefs)
        host = _query_param(href_blob, "host")
        if not host and row and _severity_from_class(row[0].classes)[0] is None:
            host = row[0].text
        if not host:
            host = last_host
        if host:
            last_host = host
        service = _query_param(href_blob, "service")
        if not service and len(row) > 1:
            service = row[1].text
        duration = ""
        if len(row) >= 5:
            match = DURATION_RE.search(row[4].text)
            if match:
                duration = match.group(1)
        if not duration:
            match = DURATION_RE.search(blob)
            duration = match.group(1) if match else ""
        info = row[-1].text if row else ""
        if "ACKNOWLEDGED" in f"{blob} {href_blob}".upper():
            ack = True
        alertname = service or "NagiosAlert"
        app = host or "N/A"
        alerts.append(
            Alert(
                server=server.name,
                severity=Severity(severity),
                alertname=alertname,
                app=app,
                desc=(info[:120] if info else alertname),
                status_text=info,
                duration_str=duration,
                acknowledged=ack,
                host=host,
            )
        )
    return alerts


class NagiosCgiHttpClient:
    def __init__(
        self,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def fetch(self, server: MonitorServer) -> list[Alert]:
        url = f"{server.url.rstrip('/')}{CGI_SUFFIX}"
        client = build_http_client(server, self._timeout_seconds, self._transport)
        try:
            response = client.get(url)
            if response.status_code != 200:
                log_fetch_failed(
                    server,
                    error_type="http_status",
                    http_status=response.status_code,
                    exc_info=logging.getLogger(__name__).isEnabledFor(logging.DEBUG),
                )
                return []
            return _alerts_from_html(server, response.text)
        except httpx.HTTPError as exc:
            log_fetch_failed(
                server,
                error_type=type(exc).__name__,
                exc_info=logging.getLogger(__name__).isEnabledFor(logging.DEBUG),
            )
            return []
        finally:
            client.close()
