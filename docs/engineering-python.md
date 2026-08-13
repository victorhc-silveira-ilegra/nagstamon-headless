# Engenharia Python

Guia de engenharia do daemon `nagstamon-headless` (camadas, qualidade, config e runtime).

## Objetivos

- Hexagonal / DDD com cobertura 100%
- Composition root no worker
- Logging semantico enxuto (ver [engineering-logging.md](engineering-logging.md))
- Config centralizada no `.env` da raiz
- Sem comentarios no codigo de aplicacao

## Fluxo de runtime

1. Worker parseia `--max-cycles` (opcional)
2. `Settings.from_env()` carrega `.env` (salvo `NAGSTAMON_DISABLE_DOTENV`); falha emite `worker.boot.failed`
3. Setup de logging (`LOG_LEVEL` / `LOG_FORMAT` / `LOG_FILE`) e `worker.started`
4. `CycleGuard.try_enter()`; se ocupado emite `poll.cycle.skipped_in_flight` (WARNING)
5. Emite `poll.cycle.started`
6. `PollMonitorsUseCase.execute()`: config → fetch → filtro → claim → sink
7. Worker emite `monitor.config.empty` (uma vez, se `servers_count=0`), `poll.alert.skipped_duplicate` (se houver), `poll.cycle.finished` (com `duration_ms`) ou `poll.cycle.failed`
8. Sleep `REFRESH_INTERVAL` e repete

## Ports e adapters

| Port | Adapter | Notas |
|------|---------|--------|
| `ServerConfigPort` | `IniServerConfigAdapter` | `*.conf` estilo Nagstamon |
| `MonitorClientPort` | `CompositeMonitorClient` | httpx; fail-open por servidor |
| `AlertSinkPort` | `StdoutAlertSink` | saida operacional (nao e log) |
| `ClockPort` | `SystemClock` | UTC |
| `AlertDispatchLedgerPort` | `InMemoryAlertDispatchLedger` | `try_claim` atomico no processo |

Ports sao `typing.Protocol` (sem ABC).

## Domain services

`AlertFilterPolicy`:

- texto de erro de conexao / URL invalida
- duracao &lt; 5 min ou ≥ 2 dias
- Watchdog / InfoInhibitor
- states suppressed/pending/unprocessed e silenced/inhibited

## Qualidade

| Comando | O que roda |
|---------|------------|
| `make app-lint` | Ruff, mypy strict, vulture, limite 300 linhas |
| `make app-test` | pytest-xdist + coverage 100% (branch) |
| `make app-security` | bandit + pip-audit |
| `make app-pre-commit-run` | hooks em todos os arquivos (requer git) |

CI (GitHub Actions): [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — lint, test e security em paralelo; `release` com semantic-release em `main`.

Orquestrador: `app/scripts/operations/clean_workspace.py`.

Convencoes:

- Conventional Commits (`linters/commitlint.config.mjs`)
- Sem emojis em codigo / logs / docs tecnicas
- Sem comentarios no codigo Python de `app/src`

## Testes

```text
app/tests/
├── unit/domain/
├── unit/application/
├── unit/infrastructure/
├── unit/presentation/
└── integration/infrastructure/
```

`conftest.py` define `NAGSTAMON_DISABLE_DOTENV=1` para isolar testes do `.env` local.

Fakes/Mocks: fakes dos ports, `httpx.BaseTransport`, sleeper injetavel no worker.

## Config e segredos

- `.env` na raiz (nao versionado); template em `.env.example`
- Compose: `docker compose --env-file .env ...`
- Python: `load_project_dotenv(override=True)` em `Settings.from_env()`
- Nunca commitar proxy interno real nem senhas dos `.conf`

## Entrypoints

- Local: `make app-run` / `python run.py`
- Console script: `nagstamon-headless`
- Docker: `make docker-up` (CMD `nagstamon-headless`)
