from __future__ import annotations

import base64
import binascii
import zlib

_ROUNDS = 5


def deobfuscate(raw: str) -> str:
    if not raw:
        return raw
    try:
        blob = base64.b64decode(raw)
        for _ in range(_ROUNDS):
            blob = zlib.decompress(blob)
            reversed_b64 = blob.decode("ascii")[::-1]
            blob = base64.b64decode(reversed_b64)
        return blob.decode("utf-8")
    except (ValueError, UnicodeError, binascii.Error, zlib.error):
        return raw
