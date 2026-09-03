from __future__ import annotations

from collections.abc import Callable

from operations.gates import docker_area, github_area, python_area, scripts_area

AREAS = ("python", "docker", "github", "scripts")
STAGES = ("lint", "security", "test", "validate", "build", "clean", "pytest")

_DISPATCH: dict[str, dict[str, Callable[..., None]]] = {
    "python": {
        "lint": python_area.lint,
        "security": python_area.security,
        "test": python_area.test,
        "pytest": python_area.test,
        "validate": python_area.validate,
        "build": python_area.build,
        "clean": python_area.stage_clean,
    },
    "docker": {
        "lint": docker_area.lint,
        "security": docker_area.security,
        "test": docker_area.test,
        "validate": docker_area.validate,
        "build": docker_area.build,
    },
    "github": {
        "lint": github_area.lint,
        "security": github_area.security,
        "test": github_area.test,
        "validate": github_area.validate,
        "build": github_area.build,
    },
    "scripts": {
        "lint": scripts_area.lint,
        "security": scripts_area.security,
        "test": scripts_area.test,
        "validate": scripts_area.validate,
        "build": scripts_area.build,
    },
}


def run_area_stage(
    area: str,
    stage: str,
    *,
    coverage_fail_under: int = 100,
    light_clean: bool = False,
) -> None:
    handlers = _DISPATCH.get(area)
    if handlers is None:
        print(f"\n[ERRO] Area desconhecida: {area}")
        raise SystemExit(1)
    handler = handlers.get(stage)
    if handler is None:
        print(f"\n[ERRO] Stage '{stage}' nao suportado na area '{area}'")
        raise SystemExit(1)
    if area == "python" and stage in {"test", "pytest"}:
        handler(coverage_fail_under)
        return
    if area == "python" and stage == "clean":
        handler(light=light_clean)
        return
    handler()
