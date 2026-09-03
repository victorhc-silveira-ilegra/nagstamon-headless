from __future__ import annotations

import re
from pathlib import Path

from operations.gates.common import (
    GITHUB_DIR,
    REPO_ROOT,
    require_binary,
    run_cmd,
    stage_ok,
)

_REQUIRED_ACTIONS = (
    GITHUB_DIR / "actions" / "ci" / "setup-python" / "action.yml",
    GITHUB_DIR / "actions" / "ci" / "validate-docker" / "action.yml",
    GITHUB_DIR / "actions" / "ci" / "validate-github" / "action.yml",
    GITHUB_DIR / "actions" / "ci" / "validate-scripts" / "action.yml",
    GITHUB_DIR / "actions" / "ci" / "release" / "action.yml",
    GITHUB_DIR / "actions" / "ci" / "sync-tags" / "action.yml",
    GITHUB_DIR / "actions" / "shared" / "pipeline-summary" / "action.yml",
    GITHUB_DIR / "workflows" / "ci.yml",
)
_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"][^'\"]{8,}"
)


def _yaml_files() -> list[Path]:
    files: list[Path] = []
    for pattern in ("**/*.yml", "**/*.yaml"):
        files.extend(GITHUB_DIR.glob(pattern))
    return sorted(files)


def _workflow_files() -> list[Path]:
    workflows = GITHUB_DIR / "workflows"
    files = sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml"))
    return [path for path in files if path.is_file()]


def lint() -> None:
    actionlint = require_binary("actionlint")
    files = _workflow_files()
    if not files:
        print("\n[ERRO] Nenhum workflow em .github/workflows")
        raise SystemExit(1)
    run_cmd(
        [actionlint, "-color", *[str(path) for path in files]],
        description="actionlint workflows",
        cwd=REPO_ROOT,
    )
    stage_ok("Lint GitHub concluido")


def security() -> None:
    gitleaks = require_binary("gitleaks")
    run_cmd(
        [
            gitleaks,
            "detect",
            "--source",
            str(GITHUB_DIR),
            "--no-git",
            "--verbose",
            "--redact",
        ],
        description="Gitleaks .github",
    )
    for path in _yaml_files():
        text = path.read_text(encoding="utf-8")
        if _SECRET_PATTERN.search(text):
            print(
                f"\n[ERRO] Possivel segredo hardcoded em {path.relative_to(REPO_ROOT)}"
            )
            raise SystemExit(1)
    stage_ok("Seguranca GitHub concluida")


def test() -> None:
    actionlint = require_binary("actionlint")
    files = _workflow_files()
    run_cmd(
        [actionlint, *[str(path) for path in files]],
        description="actionlint (testes de workflow)",
        cwd=REPO_ROOT,
    )
    stage_ok("Testes GitHub concluidos")


def validate() -> None:
    missing = [path for path in _REQUIRED_ACTIONS if not path.is_file()]
    if missing:
        print("\n[ERRO] Estrutura GitHub Actions incompleta:")
        for path in missing:
            print(f"  - {path.relative_to(REPO_ROOT)}")
        raise SystemExit(1)
    stage_ok("Validate GitHub concluido")


def build() -> None:
    expected = (
        GITHUB_DIR / "actions" / "ci",
        GITHUB_DIR / "actions" / "shared",
        GITHUB_DIR / "workflows",
    )
    for path in expected:
        if not path.is_dir():
            print(f"\n[ERRO] Diretorio ausente: {path.relative_to(REPO_ROOT)}")
            raise SystemExit(1)
    stage_ok("Build GitHub (estrutura de actions) concluido")
