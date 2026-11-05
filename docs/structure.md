# Estrutura do repositorio

Layout operacional do Nagstamon Headless (`app/`, `infra/`, `linters/`, `docs/`).

```text
.
├── app/
│   ├── src/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   └── services/alert_filter.py, alert_hold.py (criticidade 10/15/20 min), alert_view.py
│   │   ├── application/
│   │   │   ├── ports/
│   │   │   └── use_cases/poll_monitors.py, ping_monitors.py
│   │   ├── infrastructure/
│   │   │   ├── adapters/
│   │   │   ├── config/
│   │   │   └── logging/
│   │   └── presentation/
│   │       ├── worker/main.py
│   │       ├── worker/cycle_guard.py
│   │       ├── cli/ping.py
│   │       └── logging/ (config.py, daily.py, formatters)
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── scripts/
│   │   ├── setup.sh
│   │   └── operations/clean_workspace.py, gates/
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── requirements-dev.txt
├── logs/ (.gitkeep; `nagstamon-YYYY-MM-DD.log` no host, ignorado pelo git)
├── docs/
├── infra/docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── smoke.sh
│   └── .hadolint.yaml
├── linters/
│   └── releaserc.json
├── .github/
│   ├── actions/
│   │   ├── ci/ (setup-python, validate-*, release, sync-tags)
│   │   └── shared/pipeline-summary/
│   └── workflows/
│       ├── ci.yml
│       └── templates/release-announcement.yaml
├── Makefile
├── AGENTS.md
├── prompt-model.md
├── .env.example
├── .cursor/rules/
├── .cursor/skills/
└── run.py
```

## Regras de dependencia

- `domain` e `application` **nao** importam `infrastructure` nem `presentation`.
- `infrastructure` e `presentation` dependem de `application` / `domain`.
- `presentation/worker` e o **composition root** do daemon: instancia Settings, adapters (incluindo filtro, som, Google Chat e ledger) e o use case de poll.
- `presentation/cli/ping` e o composition root one-shot de `make app-ping` (probe HTTP + `enabled` nos `*.conf`).
- Qualidade operacional vive em `app/scripts/operations` (`make app-lint|app-test|app-security`; matriz `--area`/`--stage` em [docs/devops.md](devops.md)).

## Pacotes Python (imports)

`pythonpath` / editable install apontam para `app/src`. Imports absolutos:

```python
from domain.entities.alert import Alert
from application.use_cases.poll_monitors import PollMonitorsUseCase
from infrastructure.config.settings import Settings
from presentation.worker.main import run
from presentation.cli.ping import run as ping_run
```

Sem prefixo `app.src`.
