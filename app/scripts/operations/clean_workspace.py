from __future__ import annotations

import argparse
import ctypes
import gc
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = APP_ROOT.parent

if str(APP_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(APP_ROOT / "src"))

RemoveFn = Callable[[Path], None]
_CACHE_NAMES = (
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    "dist",
    "build",
    ".mypy_cache",
)
_SKIP_WALK_DIRS = frozenset({".venv", "venv", ".git", ".idea", ".vscode"})
_STAGE_MODULES: dict[str, tuple[str, ...]] = {
    "lint": ("ruff", "mypy", "vulture"),
    "test": ("coverage", "pytest", "xdist", "pytest_cov"),
    "pytest": ("coverage", "pytest", "xdist", "pytest_cov"),
    "security": ("bandit", "pip_audit"),
    "clean": (),
}
_VERBOSE = os.environ.get("NAGSTAMON_TEST_VERBOSE", "0") == "1"
_PYTEST_COMMON_ARGS = (
    "-q",
    "--tb=short",
    "-p",
    "no:cacheprovider",
    "-p",
    "no:stepwise",
)


@dataclass(frozen=True)
class TestExecutionProfile:
    name: str
    parallel_workers: int
    available_ram_gb: float | None


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


def _available_ram_gb() -> float | None:
    result: float | None = None
    if sys.platform == "linux":
        try:
            with Path("/proc/meminfo").open(encoding="utf-8") as meminfo:
                for line in meminfo:
                    if line.startswith("MemAvailable:"):
                        result = int(line.split()[1]) / (1024 * 1024)
                        break
        except OSError:
            result = None
    return result


def resolve_test_execution_profile() -> TestExecutionProfile:
    cpu_cap = os.cpu_count() or 4
    avail = _available_ram_gb()
    if avail is None:
        return TestExecutionProfile("fallback", max(2, min(4, cpu_cap)), None)
    tiers = (
        (8, "ram-8gb", 2),
        (16, "ram-16gb", 4),
        (32, "ram-32gb", 6),
    )
    for threshold, name, workers in tiers:
        if avail < threshold:
            return TestExecutionProfile(name, min(workers, cpu_cap), avail)
    return TestExecutionProfile("ram-64gb", min(8, cpu_cap), avail)


def format_profile_summary(profile: TestExecutionProfile) -> str:
    ram = (
        "desconhecida"
        if profile.available_ram_gb is None
        else f"{profile.available_ram_gb:.1f} GiB"
    )
    return f"perfil={profile.name} | workers={profile.parallel_workers} | RAM={ram}"


def _venv_python_candidates() -> list[Path]:
    candidates: list[Path] = []
    cfg = REPO_ROOT / "config" / "python.json"
    venv_name = ".venv"
    if cfg.is_file():
        data = json.loads(cfg.read_text(encoding="utf-8"))
        configured = data.get("venv_path")
        if isinstance(configured, str) and configured:
            venv_name = configured
    candidates.append(REPO_ROOT / venv_name / "bin" / "python")
    candidates.append(APP_ROOT / venv_name / "bin" / "python")
    return candidates


def _imports_available(python: Path, modules: tuple[str, ...]) -> bool:
    if not modules:
        return True
    try:
        if not python.exists():
            return False
    except OSError:
        return False
    imports = "; ".join(f"import {module}" for module in modules)
    return (
        subprocess.run(
            [str(python), "-c", imports],
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        ).returncode
        == 0
    )


def _ensure_project_python(stage: str) -> None:
    modules = _STAGE_MODULES.get(stage, ())
    current = Path(sys.executable)
    if _imports_available(current, modules):
        return
    for candidate in _venv_python_candidates():
        try:
            exists = candidate.exists()
        except OSError:
            continue
        if not exists or os.path.normcase(str(candidate)) == os.path.normcase(
            str(current)
        ):
            continue
        if _imports_available(candidate, modules):
            raise SystemExit(
                subprocess.run(
                    [str(candidate), *map(str, sys.argv)],
                    check=False,
                    shell=False,
                ).returncode
            )
    if modules:
        print(
            f"\n[ERRO] Dependencias ausentes para o estagio '{stage}': {', '.join(modules)}"
        )
        print("Instale com: make app-install")
    raise SystemExit(1)


def _use_app_cwd() -> None:
    os.chdir(APP_ROOT)


def run_tool(module: str, args: list[str], description: str) -> None:
    print(f"\n>>> Executando: {description}")
    command = [sys.executable, "-m", module, *args]
    if _VERBOSE:
        print(f"Command: {' '.join(command)}")
    subprocess.run(command, check=True, text=True, shell=False)


def _run_subprocess(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    if _VERBOSE:
        subprocess.run(command, check=True, text=True, shell=False, cwd=cwd, env=env)
        return
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        shell=False,
        cwd=cwd,
        env=env,
        capture_output=True,
    )
    if completed.returncode == 0:
        return
    if completed.stdout:
        print(completed.stdout)
    if completed.stderr:
        print(completed.stderr)
    raise subprocess.CalledProcessError(
        completed.returncode,
        command,
        output=completed.stdout,
        stderr=completed.stderr,
    )


def _purge_coverage_artifacts(app_root: Path) -> None:
    for pattern in (".coverage", ".coverage.*"):
        for artifact in app_root.glob(pattern):
            artifact.unlink(missing_ok=True)


def _release_parent_memory() -> None:
    gc.collect()
    if sys.platform != "linux":
        return
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        return


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


def clean_workspace_artifacts(
    app_root: Path, repo_root: Path, safe_remove: RemoveFn
) -> None:
    for scan_root in (app_root, repo_root):
        clean_named_caches(scan_root, safe_remove)
        clean_python_artifacts(scan_root, safe_remove)
    logs_dir = repo_root / "logs"
    if logs_dir.exists():
        for child in list(logs_dir.iterdir()):
            if child.name == ".gitkeep":
                continue
            safe_remove(child)
    for pattern in (
        repo_root.glob("pytest-cache-files-*"),
        app_root.glob("pytest-cache-files-*"),
    ):
        for stray in pattern:
            safe_remove(stray)


def stage_clean(*, light: bool = False) -> None:
    print("\n>>> Executando: Limpeza de lixo e caches")
    safe_remove = build_safe_remove()
    clean_workspace_artifacts(APP_ROOT, REPO_ROOT, safe_remove)
    if light:
        return
    egg_info = APP_ROOT / "src" / "nagstamon_headless.egg-info"
    if egg_info.exists():
        safe_remove(egg_info)


def stage_structure(max_lines: int = 300) -> None:
    print(f"\n>>> Executando: Verificacao Estrutural (Max {max_lines} linhas)")
    violations: list[str] = []
    src_root = APP_ROOT / "src"
    for path in src_root.rglob("*.py"):
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > max_lines:
            violations.append(f"{path}: {count} linhas")
    if violations:
        print("\n[ERRO] Violacao de limite de linhas encontrada:")
        for violation in violations:
            print(f"  - {violation}")
        raise SystemExit(1)
    print(f"[OK] Todos os arquivos estao abaixo de {max_lines} linhas.")


def stage_lint() -> None:
    print("\n>>> Executando: Ruff Check (auto-fix)")
    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--fix", "src", "tests"],
        check=True,
        text=True,
        shell=False,
    )
    run_tool("ruff", ["format", "src", "tests"], "Ruff Format")
    run_tool("ruff", ["check", "src", "tests"], "Ruff Check")
    run_tool("mypy", ["--config-file=pyproject.toml"], "Mypy Strict")
    run_tool("vulture", ["src"], "Vulture Dead Code Detection")
    stage_structure()


def _test_env_base() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("COVERAGE_CORE", "sysmon")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def stage_test(fail_under: int = 100) -> None:
    profile = resolve_test_execution_profile()
    workers = profile.parallel_workers
    print(f"\n>>> {format_profile_summary(profile)}")
    _purge_coverage_artifacts(APP_ROOT)
    env = _test_env_base()
    command = [
        sys.executable,
        "-m",
        "pytest",
        *_PYTEST_COMMON_ARGS,
        "--import-mode=importlib",
        "-n",
        str(workers),
        "--cov=domain",
        "--cov=application",
        "--cov=infrastructure",
        "--cov=presentation",
        "--cov-report=term-missing",
        f"--cov-fail-under={fail_under}",
        "tests/",
    ]
    print(f">>> pytest-xdist + pytest-cov ({workers} workers)")
    _run_subprocess(command, cwd=APP_ROOT, env=env)
    _release_parent_memory()


def stage_security() -> None:
    run_tool("bandit", ["-r", "src", "-c", "pyproject.toml"], "Bandit Security Scan")
    try:
        run_tool("pip_audit", ["--local"], "Pip-audit Vulnerability Scan")
    except subprocess.CalledProcessError:
        print(
            "[AVISO] Pip-audit encontrou vulnerabilidades no ambiente de pacotes Python."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Nagstamon Headless Quality Gate")
    parser.add_argument(
        "--stage",
        required=True,
        choices=["lint", "pytest", "security", "test", "clean"],
        help="Stage to execute",
    )
    parser.add_argument(
        "--coverage-fail-under",
        type=int,
        default=100,
        help="Minimum coverage percentage",
    )
    parser.add_argument(
        "--light-clean",
        action="store_true",
        help="Limpa apenas caches sem remover artefatos de build",
    )
    args = parser.parse_args()
    _ensure_project_python(args.stage)
    _use_app_cwd()
    if args.stage == "lint":
        stage_lint()
    elif args.stage in ("pytest", "test"):
        stage_test(args.coverage_fail_under)
    elif args.stage == "security":
        stage_security()
    elif args.stage == "clean":
        stage_clean(light=args.light_clean)
    print("\n[SUCESSO] Estagio concluido com sucesso.")


if __name__ == "__main__":
    main()
