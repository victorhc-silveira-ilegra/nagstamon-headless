from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_project_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NAGSTAMON_DISABLE_DOTENV", "1")
