from __future__ import annotations

from pathlib import Path


def load_dotenv_file(path: Path, *, override: bool = False) -> None:
    import os

    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value


def load_project_dotenv(
    *, override: bool = False, start: Path | None = None
) -> Path | None:
    here = (start or Path(__file__)).resolve()
    for parent in here.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            load_dotenv_file(candidate, override=override)
            return candidate
    return None
