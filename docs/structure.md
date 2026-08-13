# Estrutura do repositorio

Layout operacional do Nagstamon Headless (`app/`, `infra/`, `linters/`, `docs/`).

```text
.
├── app/
│   ├── src/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   └── services/alert_filter.py
│   │   ├── application/
│   │   │   ├── ports/
│   │   │   └── use_cases/poll_monitors.py
│   │   ├── infrastructure/
│   │   │   ├── adapters/
│   │   │   ├── config/
│   │   │   └── logging/
│   │   └── presentation/
│   │       ├── worker/main.py
│   │       ├── worker/cycle_guard.py
│   │       └── logging/
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── scripts/
│   │   ├── setup.sh
│   │   └── operations/clean_workspace.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docs/
├── infra/docker/
├── linters/
│   └── releaserc.json
├── .github/
│   ├── actions/
│   │   ├── lint/
│   │   ├── test/
│   │   ├── security/
│   │   ├── release/
│   │   └── sync-tags/
│   └── workflows/
│       ├── ci.yml
│       └── templates/release-announcement.yaml
├── Makefile
├── AGENTS.md
├── prompt-model.md
├── .env.example
└── run.py
```

## Regras de dependencia

- `domain` e `application` **nao** importam `infrastructure` nem `presentation`.
- `infrastructure` e `presentation` dependem de `application` / `domain`.
- `presentation/worker` e o **composition root**: instancia Settings, adapters e o use case.
- Qualidade operacional vive em `app/scripts/operations` (`make app-lint|app-test|app-security`).

## Pacotes Python (imports)

`pythonpath` / editable install apontam para `app/src`. Imports absolutos:

```python
from domain.entities.alert import Alert
from application.use_cases.poll_monitors import PollMonitorsUseCase
from infrastructure.config.settings import Settings
from presentation.worker.main import run
```

Sem prefixo `app.src`.
