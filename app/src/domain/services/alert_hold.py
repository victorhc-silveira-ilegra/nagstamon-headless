from __future__ import annotations

import re

from domain.entities.alert import Alert

HOLD_FAST_SECONDS = 600
HOLD_CRITICAL_SECONDS = 900
HOLD_WARNING_SECONDS = 1200
_PAGING = frozenset({"CRITICAL", "WARNING"})
_FAST = re.compile(
    r"(?i)(?:"
    r"(?<![a-z])down(?![a-z])|unreachable|"
    r"crashloop|oomkilled|(?<![a-z])oom(?![a-z])|java\s*heap|"
    r"burn_?rate|error_?budget|"
    r"notready|not_ready|failedmount|failed_mount|"
    r"quorum|(?<![a-z])leader(?![a-z])|replicac(?:ao|ion)|"
    r"stopped|parado|interrompido|"
    r"connection\s*refused|socket\s*timeout|"
    r"(?<![a-z])pix(?![a-z])|bacen|bcb2?|celcoin|"
    r"redo\s*log|"
    r"disk|(?<![a-z])disco(?![a-z])|filesystem|tablespace|inode|"
    r"certificate|certificado|(?<![a-z])cert(?![a-z])|(?<![a-z])tls(?![a-z])|expir(?:ed|ing|a|ado|acao|ation)|"
    r"payment|pagamento|(?<![a-z])login(?![a-z])|(?<![a-z])sso(?![a-z])"
    r")"
)
_TRANSIENT = re.compile(
    r"(?i)(?:"
    r"cpu|memory|memoria|(?<![a-z])mem(?![a-z])|(?<!down)load|"
    r"throttl|queue|(?<![a-z])fila(?![a-z])|(?<![a-z])lock(?![a-z])|deadlock|"
    r"(?<![a-z])ping(?![a-z])|latenc|(?<![a-z])flap(?![a-z])"
    r")"
)


def _haystack(alert: Alert) -> str:
    return f"{alert.alertname} {alert.desc} {alert.status_text}"


def hold_seconds(
    alert: Alert,
    *,
    fast: int = HOLD_FAST_SECONDS,
    critical: int = HOLD_CRITICAL_SECONDS,
    warning: int = HOLD_WARNING_SECONDS,
) -> int | None:
    if alert.severity.value not in _PAGING:
        return None
    text = _haystack(alert)
    if _FAST.search(text):
        return fast
    if _TRANSIENT.search(text):
        return warning
    if alert.severity.value == "CRITICAL":
        return critical
    return warning
