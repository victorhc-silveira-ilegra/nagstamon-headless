from __future__ import annotations

import io
import logging
import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path
from shutil import which

from infrastructure.logging import POLL_SOUND_FAILED, log_event

logger = logging.getLogger(__name__)
PAPLAY_VOLUME = "18000"
SAMPLE_RATE = 22050
DURATION_SECONDS = 0.25
FREQUENCY_HZ = 440.0
AMPLITUDE = 0.2


def _wav_bytes() -> bytes:
    buffer = io.BytesIO()
    frames = int(SAMPLE_RATE * DURATION_SECONDS)
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        payload = bytearray()
        for index in range(frames):
            sample = int(
                AMPLITUDE
                * 32767
                * math.sin(2 * math.pi * FREQUENCY_HZ * index / SAMPLE_RATE)
            )
            payload.extend(struct.pack("<h", sample))
        wav.writeframes(payload)
    return buffer.getvalue()


class PopenAlertSound:
    def play_new_alert(self) -> None:
        player = which("paplay") or which("aplay")
        if player is None:
            log_event(
                logger,
                logging.WARNING,
                POLL_SOUND_FAILED,
                error_type="missing_player",
            )
            return
        path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                handle.write(_wav_bytes())
                path = Path(handle.name)
            command = [player, str(path)]
            if Path(player).name == "paplay":
                command = [player, f"--volume={PAPLAY_VOLUME}", str(path)]
            subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=5,
                shell=False,
            )
        except Exception as exc:
            log_event(
                logger,
                logging.WARNING,
                POLL_SOUND_FAILED,
                error_type=type(exc).__name__,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
        finally:
            if path is not None:
                path.unlink(missing_ok=True)
