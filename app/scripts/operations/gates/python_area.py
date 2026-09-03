from __future__ import annotations

import ctypes
import gc
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from operations.gates.common import (
    APP_ROOT,
    REPO_ROOT,
    STAGE_MODULES,
    build_safe_remove,
    clean_named_caches,
    clean_python_artifacts,
    run_cmd,
    run_tool,
    stage_ok,
)

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


def ensure_project_python(stage: str) -> None:
    modules = STAGE_MODULES.get(stage, ())
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
            f"\n[ERRO] Dependencias ausentes para o estagio '{stage}': "
            f"{', '.join(modules)}"
        )
        print("Instale com: make app-install")
    raise SystemExit(1)


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


def _test_env_base() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("COVERAGE_CORE", "sysmon")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def _run_subprocess(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    if os.environ.get("NAGSTAMON_TEST_VERBOSE", "0") == "1":
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


def stage_clean(*, light: bool = False) -> None:
    print("\n>>> Executando: Limpeza de lixo e caches")
    safe_remove = build_safe_remove()
    from presentation.logging.daily import resolve_log_timezone, stale_daily_log_paths

    for scan_root in (APP_ROOT, REPO_ROOT):
        clean_named_caches(scan_root, safe_remove)
        clean_python_artifacts(scan_root, safe_remove)
    logs_dir = REPO_ROOT / "logs"
    if logs_dir.exists():
        today = datetime.now(
            resolve_log_timezone(os.environ.get("WINDOW_TIMEZONE"))
        ).date()
        for child in stale_daily_log_paths(logs_dir, today):
            safe_remove(child)
    for pattern in (
        REPO_ROOT.glob("pytest-cache-files-*"),
        APP_ROOT.glob("pytest-cache-files-*"),
    ):
        for stray in pattern:
            safe_remove(stray)
    if light:
        return
    egg_info = APP_ROOT / "src" / "nagstamon_headless.egg-info"
    if egg_info.exists():
        safe_remove(egg_info)


def lint() -> None:
    print("\n>>> Executando: Ruff Check (auto-fix)")
    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--fix", "src", "tests"],
        check=True,
        text=True,
        shell=False,
        cwd=APP_ROOT,
    )
    run_tool("ruff", ["format", "src", "tests"], "Ruff Format")
    run_tool("ruff", ["check", "src", "tests"], "Ruff Check")
    run_tool("mypy", ["--config-file=pyproject.toml"], "Mypy Strict")
    run_tool("vulture", ["src"], "Vulture Dead Code Detection")
    stage_structure()


def security() -> None:
    run_tool("bandit", ["-r", "src", "-c", "pyproject.toml"], "Bandit Security Scan")
    try:
        run_tool("pip_audit", ["--local"], "Pip-audit Vulnerability Scan")
    except subprocess.CalledProcessError:
        print(
            "[AVISO] Pip-audit encontrou vulnerabilidades no ambiente de pacotes Python."
        )


def test(fail_under: int = 100) -> None:
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


def validate() -> None:
    run_cmd(
        [sys.executable, "-m", "pip", "install", "-e", str(APP_ROOT)],
        description="pip install -e app",
        cwd=REPO_ROOT,
    )
    run_cmd(
        [
            sys.executable,
            "-c",
            "from presentation.worker.main import build_parser; build_parser()",
        ],
        description="Import smoke presentation.worker.main",
        cwd=APP_ROOT,
    )
    stage_ok("Validate Python concluido")


def build() -> None:
    pyproject = APP_ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    required = ("[project]", "name =", "version =", "requires-python")
    missing = [item for item in required if item not in text]
    if missing:
        print(f"\n[ERRO] Metadados ausentes em pyproject.toml: {', '.join(missing)}")
        raise SystemExit(1)
    run_cmd(
        [sys.executable, "-m", "pip", "install", "build"],
        description="Instalar build",
        cwd=REPO_ROOT,
        check=False,
    )
    run_cmd(
        [sys.executable, "-m", "build", "--outdir", str(APP_ROOT / "dist")],
        description="python -m build",
        cwd=APP_ROOT,
    )
    stage_ok("Build Python concluido")
