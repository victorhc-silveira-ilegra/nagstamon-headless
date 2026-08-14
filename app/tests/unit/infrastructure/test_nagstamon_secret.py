from __future__ import annotations

import base64
import zlib

from infrastructure.adapters.nagstamon_secret import deobfuscate


def _obfuscate(plain: str, rounds: int = 5) -> str:
    blob = plain.encode()
    for _ in range(rounds):
        encoded = base64.b64encode(blob).decode()
        blob = zlib.compress(encoded[::-1].encode())
    return base64.b64encode(blob).decode()


def test_deobfuscate_roundtrip() -> None:
    assert deobfuscate(_obfuscate("monitor-user")) == "monitor-user"
    assert deobfuscate(_obfuscate("p@ss w0rd")) == "p@ss w0rd"


def test_deobfuscate_keeps_plaintext_and_empty() -> None:
    assert deobfuscate("") == ""
    assert deobfuscate("user") == "user"
    assert deobfuscate("not-valid-%%") == "not-valid-%%"
    garbage = base64.b64encode(zlib.compress(b"\xff\xfe")).decode()
    assert deobfuscate(garbage) == garbage
