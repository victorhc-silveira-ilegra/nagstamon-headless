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
6. `PollMonitorsUseCase.execute()`: config → fetch → filtro → claim/publish/confirm por alerta (stdout + Google Chat) → som (se claimed)
7. Worker emite `monitor.config.empty` (uma vez, se `servers_count=0`), `poll.alert.skipped_duplicate` (se houver), `poll.cycle.finished` (com `duration_ms`) ou `poll.cycle.failed`
8. Sleep `REFRESH_INTERVAL` e repete

## Ports e adapters

| Port | Adapter | Notas |
|------|---------|--------|
| `ServerConfigPort` | `IniServerConfigAdapter` | `*.conf` estilo Nagstamon; username/password desofuscados |
| `MonitorClientPort` | `CompositeMonitorClient` | httpx; fail-open por servidor |
| `AlertSinkPort` | `StdoutAlertSink` + `GoogleChatWebhookSink` via `CompositeAlertSink` | cards no stdout e no webhook; Chat raises apos log para o ledger dar release |
| `ClockPort` | `SystemClock` | UTC |
| `AlertDispatchLedgerPort` | `FileAlertDispatchLedger` / `InMemoryAlertDispatchLedger` | `try_claim` / `confirm` / `release`; arquivo com flock se `DEDUP_LEDGER_PATH` |
| `AlertSoundPort` | `PopenAlertSound` | WAV 440 Hz; `paplay`/`aplay`; fail-open |

Ports sao `typing.Protocol` (sem ABC).

## Domain services

`AlertFilterPolicy` (janela e fuso injetados pelo worker a partir do `.env`):

- `acknowledged=True` (Nagios); no Alertmanager, `silenced_by` equivale a ack
- duracao e horario so em Python, via `.env`: &lt; `FILTER_DURATION_MIN_SECONDS` ou ≥ `FILTER_DURATION_MAX_SECONDS` (defaults 600 / 86400) via `starts_at` ou parse de `duration_str`; sem regex do GUI
- janela diaria `[FILTER_WINDOW_START, FILTER_WINDOW_END]` em `FILTER_TIMEZONE`: `now` no intervalo **e**, se o inicio for conhecido, esse instante no mesmo intervalo hoje; CGI sem `starts_at`/`duration_str` so usa a janela de `now`
- texto de erro de conexao / URL invalida
- Watchdog / InfoInhibitor
- states suppressed/pending/unprocessed e silenced/inhibited

`AlertView` (`domain/services/alert_view.py`): snapshot operacional em cards alinhados (CRITICAL primeiro). Campos: Client (`server`), Host (`host` ou `app`), Service (`alertname`), Status (`severity`), Duration (`duration_str` ou `starts_at`), Started (`starts_at` no fuso, `DD/MM/YYYY HH:MM:SS`), Status information (`status_text` ou `desc`). Placeholder `N/A` / vazio vira `--`.

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
- `FILTER_WINDOW_START` / `FILTER_WINDOW_END` (`HH:MM`), `FILTER_TIMEZONE` (IANA), `FILTER_DURATION_MIN_SECONDS` / `FILTER_DURATION_MAX_SECONDS`, `SOUND_ENABLED` (default true; compose forca `false`), `GCHAT_WEBHOOK_URL` (vazio = desligado; so no `.env` local), `DEDUP_LEDGER_PATH` (vazio = memoria)

## Entrypoints

- Local: `make app-run` / `python run.py`
- Console script: `nagstamon-headless`
- Docker: `make docker-up` (CMD `nagstamon-headless`); `make docker-smoke` (1 ciclo real via VPN/proxy e `*.conf`)
