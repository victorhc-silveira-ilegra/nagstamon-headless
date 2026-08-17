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
3. Tee de stdout/stderr para `LOG_DIR` (arquivo do dia), setup de logging (`LOG_LEVEL` / `LOG_FORMAT` / `LOG_FILE`) e `worker.started`
4. `CycleGuard.try_enter()`; se ocupado emite `poll.cycle.skipped_in_flight` (WARNING)
5. Emite `poll.cycle.started` no primeiro ciclo
6. `PollMonitorsUseCase.execute()`: config → fetch → filtro → claim/publish/confirm por alerta (stdout + Google Chat) → som (se claimed)
7. Worker emite `monitor.config.empty` (uma vez, se `servers_count=0`) e `poll.cycle.finished` (primeiro ciclo, ou se houver claimed; com `duration_ms` e `skipped_duplicate_count`) ou `poll.cycle.failed`
8. Sleep `REFRESH_INTERVAL_SECONDS` e repete

## Ports e adapters

| Port | Adapter | Notas |
|------|---------|--------|
| `ServerConfigPort` | `IniServerConfigAdapter` | `*.conf` estilo Nagstamon; username/password desofuscados |
| `MonitorClientPort` | `CompositeMonitorClient` | httpx; fail-open por servidor |
| `AlertSinkPort` | `StdoutAlertSink` + `GoogleChatWebhookSink` via `CompositeAlertSink` | mesmo snapshot texto no stdout e no webhook (`{"text": ...}`); Chat raises apos log para o ledger dar release |
| `ClockPort` | `SystemClock` | UTC |
| `AlertDispatchLedgerPort` | `FileAlertDispatchLedger` / `InMemoryAlertDispatchLedger` | `try_claim` / `confirm` / `release`; arquivo com flock se `DEDUP_LEDGER_PATH` |
| `AlertSoundPort` | `PopenAlertSound` | WAV 440 Hz; `paplay`/`aplay`; fail-open |

Ports sao `typing.Protocol` (sem ABC).

## Domain services

`hold_seconds` (`domain/services/alert_hold.py`): classifica criticidade de persistencia (keywords em alertname/desc/status, nao no host). Tipo ganha de severidade.

| Criticidade | Quem | Env | Default |
|-------------|------|-----|---------|
| Muito critico | DOWN/disco/cert/login | `FILTER_HOLD_FAST_SECONDS` | 600 (10 min) |
| Mediano | CRITICAL restante | `FILTER_HOLD_CRITICAL_SECONDS` | 900 (15 min) |
| Baixo | WARNING e CPU/mem/load/fila/lock/ping | `FILTER_HOLD_WARNING_SECONDS` | 1200 (20 min) |

`AlertFilterPolicy` (janela, dias uteis, fuso e holds injetados pelo worker a partir do `.env`):

- `acknowledged=True` (Nagios); no Alertmanager, `silenced_by` equivale a ack
- duracao so em Python: hold-down acima ate &lt; `FILTER_DURATION_MAX_SECONDS` (86400) via `starts_at` ou parse de `duration_str`; INFO e sem inicio conhecido nao disparam
- janela diaria `[WINDOW_START, WINDOW_END]` em `WINDOW_TIMEZONE` e em `WINDOW_DAYS` (default seg–sex), quando `WINDOW_ENABLED=true`: `now` no intervalo **e** o inicio conhecido no mesmo intervalo hoje
- inicio conhecido anterior ao boot do daemon (`not_before` no composition root): nao entra no snapshot efetivo
- texto de erro de conexao / URL invalida
- Watchdog / InfoInhibitor
- Kubernetes (`kubelet`, `kubernetes`, `k8s`, `kube` em alertname/desc/status; `pod` no alertname)
- states suppressed/pending/unprocessed e silenced/inhibited

`AlertView` (`domain/services/alert_view.py`): snapshot operacional em texto (CRITICAL primeiro). Labels em `*negrito*` (markdown do Chat) e colunas com NBSP. Campos: Client (`server`), Host (`host` ou `app`), Service (`alertname`), Status (`severity`), Duration (`duration_str` ou `starts_at`), Started (`starts_at` no fuso, `DD/MM/YYYY HH:MM:SS`), Status information (`status_text` ou `desc`). Placeholder `N/A` / vazio vira `--`. Google Chat recebe o mesmo texto como mensagem (`{"text": ...}`), sem card estruturado e sem fence monoespaçado.

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
- `WINDOW_ENABLED` (default true), `WINDOW_START` / `WINDOW_END` (`HH:MM`), `WINDOW_DAYS` (`mon,tue,wed,thu,fri`), `WINDOW_TIMEZONE` (IANA), `FILTER_HOLD_FAST_SECONDS` (600), `FILTER_HOLD_CRITICAL_SECONDS` (900), `FILTER_HOLD_WARNING_SECONDS` (1200), `FILTER_DURATION_MAX_SECONDS`, `SOUND_ENABLED` (default true; compose forca `false`), `GCHAT_WEBHOOK_URL` (vazio = desligado; so no `.env` local), `DEDUP_LEDGER_PATH` (vazio = memoria).

## Entrypoints

- Local: `make app-run` / `python run.py`
- Console script: `nagstamon-headless`
- Docker: `make docker-up` (CMD `nagstamon-headless`); `make docker-smoke` (1 ciclo real via VPN/proxy e `*.conf`)
