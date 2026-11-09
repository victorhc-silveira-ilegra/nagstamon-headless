from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
_APP_ROOT = Path(__file__).resolve().parents[2]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))
if str(_APP_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_APP_ROOT / "src"))

from operations.gates import AREAS, STAGES, run_area_stage
from operations.gates.python_area import ensure_project_python


def _print_summary(results: dict[str, str]) -> None:
    print("\n========================================================================")
    print("                      RESUMO DO PIPELINE CI/CD                          ")
    print("========================================================================")
    print("| Etapa      | Status  |")
    print("|------------|---------|")
    for step, status in results.items():
        print(f"| {step:<10} | {status:<7} |")
    print("========================================================================")


def run_pipeline(coverage_fail_under: int = 100) -> None:
    results: dict[str, str] = {}
    print("\n========================================================================")
    print("                NAGSTAMON HEADLESS - PIPELINE CI/CD LOCAL               ")
    print("========================================================================")

    print("\n>>> Executando: Commitlint (Conventional Commits)")
    ret = subprocess.run(
        ["bash", str(_APP_ROOT.parent / "linters" / "git-hooks" / "commitlint.sh")],
        check=False,
    )
    if ret.returncode != 0:
        results["Commitlint"] = "FAILED"
        _print_summary(results)
        raise SystemExit(1)
    results["Commitlint"] = "SUCCESS"

    ensure_project_python("test")

    pipeline_stages = ("lint", "security", "test", "validate", "build")
    for area in AREAS:
        print("\n========================================================================")
        print(f"                AREA: {area.upper()}                                    ")
        print("========================================================================")
        area_failed = False
        for stage in pipeline_stages:
            os.chdir(_APP_ROOT if area == "python" else _APP_ROOT.parent)
            try:
                run_area_stage(
                    area,
                    stage,
                    coverage_fail_under=coverage_fail_under,
                )
            except (SystemExit, subprocess.CalledProcessError):
                area_failed = True
                break
        if area_failed:
            results[area.capitalize()] = "FAILED"
            _print_summary(results)
            raise SystemExit(1)
        results[area.capitalize()] = "SUCCESS"

    _print_summary(results)
    print("\n[SUCESSO] Pipeline local concluido com sucesso.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Nagstamon Headless Quality Gate")
    parser.add_argument(
        "--area",
        choices=[*AREAS, "all"],
        default="all",
        help="Area tecnologica (default: all)",
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=list(STAGES),
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

    if args.stage == "pipeline":
        run_pipeline(coverage_fail_under=args.coverage_fail_under)
        return

    target_areas = (
        ("python",)
        if args.stage == "clean" and args.area == "all"
        else (AREAS if args.area == "all" else (args.area,))
    )
    if "python" in target_areas and args.stage in {
        "lint",
        "test",
        "pytest",
        "security",
        "clean",
        "validate",
        "build",
    }:
        ensure_project_python(args.stage if args.stage != "pytest" else "test")
    for area in target_areas:
        os.chdir(_APP_ROOT if area == "python" else _APP_ROOT.parent)
        run_area_stage(
            area,
            args.stage,
            coverage_fail_under=args.coverage_fail_under,
            light_clean=args.light_clean,
        )
    print("\n[SUCESSO] Estagio concluido com sucesso.")


if __name__ == "__main__":
    main()
