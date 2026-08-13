# Changelog

## 1.0.0

- Daemon headless em DDD / hexagonal (Alertmanager + Nagios CGI, filtros Nagstamon, stdout).
- Dedup in-memory (`try_claim`/`release`) e `CycleGuard` contra ciclo sobreposto.
- Logs semanticos: INFO no caminho feliz, WARNING em fail-open/overlap, ERROR em boot ou ciclo quebrado.
- Gates de qualidade Python (Ruff, mypy strict, vulture, pytest 100% branch, bandit, pip-audit).
- Runtime Docker minimo em `infra/docker`.
- CI GitHub Actions (lint, test, security, semantic-release).
