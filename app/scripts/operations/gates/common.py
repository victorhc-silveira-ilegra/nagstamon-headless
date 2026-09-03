from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = APP_ROOT.parent
DOCKER_DIR = REPO_ROOT / "infra" / "docker"
GITHUB_DIR = REPO_ROOT / ".github"

RemoveFn = Callable[[Path], None]
_VERBOSE = os.environ.get("NAGSTAMON_TEST_VERBOSE", "0") == "1"
_SKIP_WALK_DIRS = frozenset({".venv", "venv", ".git", ".idea", ".vscode"})
_CACHE_NAMES = (
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    "dist",
    "build",
    ".mypy_cache",
)
STAGE_MODULES: dict[str, tuple[str, ...]] = {
    "lint": ("ruff", "mypy", "vulture"),
    "test": ("coverage", "pytest", "xdist", "pytest_cov"),
    "pytest": ("coverage", "pytest", "xdist", "pytest_cov"),
    "security": ("bandit", "pip_audit"),
    "validate": (),
    "build": (),
    "clean": (),
}


def build_safe_remove() -> RemoveFn:
    def safe_remove(path: Path) -> None:
        try:
            if path.is_dir():
                shutil.rmtree(path)
                print(f"Removido diretorio: {path}")
            else:
                path.unlink()
                print(f"Removido arquivo: {path}")
        except OSError as exc:
            print(f"Erro ao remover {path}: {exc}")

    return safe_remove


def run_tool(module: str, args: list[str], description: str) -> None:
    print(f"\n>>> Executando: {description}")
    command = [sys.executable, "-m", module, *args]
    if _VERBOSE:
        print(f"Command: {' '.join(command)}")
    subprocess.run(command, check=True, text=True, shell=False)


def run_cmd(
    command: list[str],
    *,
    description: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"\n>>> Executando: {description}")
    if _VERBOSE:
        print(f"Command: {' '.join(command)}")
    return subprocess.run(
        command,
        check=check,
        text=True,
        shell=False,
        cwd=cwd or REPO_ROOT,
        env=env or os.environ.copy(),
    )


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        print(f"\n[ERRO] Binario '{name}' nao encontrado no PATH")
        raise SystemExit(1)
    return path


def stage_ok(message: str) -> None:
    print(f"\n[OK] {message}")


def clean_named_caches(scan_root: Path, safe_remove: RemoveFn) -> None:
    for name in _CACHE_NAMES:
        candidate = scan_root / name
        if candidate.exists():
            safe_remove(candidate)


def clean_python_artifacts(scan_root: Path, safe_remove: RemoveFn) -> None:
    for root, dirs, files in os.walk(scan_root):
        dirs[:] = [entry for entry in dirs if entry not in _SKIP_WALK_DIRS]
        for entry in list(dirs):
            if entry == "__pycache__":
                safe_remove(Path(root) / entry)
                dirs.remove(entry)
        for filename in files:
            if filename.endswith((".pyc", ".pyo", ".pyd")):
                safe_remove(Path(root) / filename)
