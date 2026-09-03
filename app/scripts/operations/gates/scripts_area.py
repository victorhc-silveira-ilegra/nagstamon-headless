from __future__ import annotations

import re
from pathlib import Path

from operations.gates.common import REPO_ROOT, run_cmd, stage_ok

_SECRET_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|token|password|secret)\s*[:=]\s*(['\"])([^'\"]{8,})\1"
)
_SCRIPT_GLOBS = (
    "infra/docker/*.sh",
    "app/scripts/*.sh",
    "linters/git-hooks/*.sh",
    "linters/git-hooks/bin/*.sh",
)
_MAKEFILE_SCRIPTS = (
    REPO_ROOT / "infra" / "docker" / "smoke.sh",
    REPO_ROOT / "app" / "scripts" / "setup.sh",
    REPO_ROOT / "linters" / "git-hooks" / "install.sh",
)


def _shell_scripts() -> list[Path]:
    files: list[Path] = []
    for pattern in _SCRIPT_GLOBS:
        files.extend(REPO_ROOT.glob(pattern))
    return sorted({path.resolve() for path in files if path.is_file()})


def lint() -> None:
    scripts = _shell_scripts()
    if not scripts:
        print("\n[ERRO] Nenhum script shell encontrado")
        raise SystemExit(1)
    for script in scripts:
        run_cmd(
            ["bash", "-n", str(script)],
            description=f"bash -n {script.relative_to(REPO_ROOT)}",
        )
    run_cmd(
        ["make", "-n", "help"],
        description="make -n help",
        cwd=REPO_ROOT,
    )
    stage_ok("Lint Scripts concluido")


def security() -> None:
    for script in _shell_scripts():
        text = script.read_text(encoding="utf-8", errors="replace")
        for match in _SECRET_PATTERN.finditer(text):
            value = match.group(2).strip()
            if value.startswith("$"):
                continue
            print(
                f"\n[ERRO] Possivel segredo hardcoded em {script.relative_to(REPO_ROOT)}"
            )
            raise SystemExit(1)
    stage_ok("Seguranca Scripts concluida")


def test() -> None:
    run_cmd(
        ["make", "help"],
        description="make help",
        cwd=REPO_ROOT,
    )
    for path in _MAKEFILE_SCRIPTS:
        if not path.is_file():
            print(f"\n[ERRO] Script citado ausente: {path.relative_to(REPO_ROOT)}")
            raise SystemExit(1)
    stage_ok("Testes Scripts concluidos")


def validate() -> None:
    makefile = REPO_ROOT / "Makefile"
    if not makefile.is_file():
        print("\n[ERRO] Makefile ausente")
        raise SystemExit(1)
    missing = [path for path in _MAKEFILE_SCRIPTS if not path.is_file()]
    if missing:
        print("\n[ERRO] Scripts obrigatorios ausentes:")
        for path in missing:
            print(f"  - {path.relative_to(REPO_ROOT)}")
        raise SystemExit(1)
    stage_ok("Validate Scripts concluido")


def build() -> None:
    for script in _shell_scripts():
        run_cmd(
            ["bash", "-n", str(script)],
            description=f"sintaxe {script.relative_to(REPO_ROOT)}",
        )
    stage_ok("Build Scripts (sintaxe) concluido")
