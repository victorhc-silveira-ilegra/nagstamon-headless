# Engenharia de logging semantico

## Objetivo

Orquestrar o daemon com poucos eventos nomeados, sem dump de payload JSON/HTML nem URL com segredo.

API: `log_event(logger, level, event, **fields)` em `infrastructure/logging/emit.py`.
Constantes em `infrastructure/logging/events.py`.

A lista de alertas efetivos no stdout e o **sink do produto** (snapshot texto), nao um evento de log. O handler de log tambem escreve em stdout para o `docker logs` nao entremear stderr no meio do snapshot. O worker faz tee de stdout/stderr para o arquivo diario em `LOG_DIR` (flush a cada escrita), com o mesmo recorte do `make docker-logs` (INFO + snapshot; sem linhas `WARNING`/`ERROR`/`DEBUG`/`CRITICAL event=`). Dominio e use case **nao** logam.

## Niveis

| Nivel | Quando |
|-------|--------|
| INFO | Caminho feliz: boot, primeiro ciclo, publish, finished (claimed ou heartbeat) |
| WARNING | Degradado, processo segue (fail-open, overlap, config vazia no boot) |
| ERROR | Boot invalido ou `execute()` estoura (worker sai com exit 1) |
| DEBUG | Apenas `exc_info` nas falhas; sem dumps extras |

## Eventos

| Evento | Nivel | Origem |
|--------|-------|--------|
| `worker.started` | INFO | worker (uma vez) |
| `worker.boot.failed` | ERROR | worker |
| `poll.cycle.started` | INFO | worker (so o primeiro ciclo) |
| `poll.cycle.finished` | INFO | worker (primeiro ciclo, ou `claimed_count>0`) |
| `poll.cycle.failed` | ERROR | worker |
| `poll.cycle.skipped_in_flight` | WARNING | worker (`CycleGuard`) |
| `poll.sink.published` | INFO | `StdoutAlertSink` |
| `poll.gchat.published` | INFO | `GoogleChatWebhookSink` (lista claimed nao vazia) |
| `poll.gchat.failed` | WARNING | `GoogleChatWebhookSink` (HTTP/rede; raises apos log; use case libera o claim) |
| `poll.sound.failed` | WARNING | `PopenAlertSound` (player ausente ou falha; fail-open) |
| `monitor.fetch.failed` | WARNING | adapters HTTP / composite (fail-open) |
| `monitor.config.failed` | WARNING | `IniServerConfigAdapter` (fail-open) |
| `monitor.config.empty` | WARNING | worker, uma vez se o primeiro ciclo tiver `servers_count=0` |
| `monitor.ping.started` | INFO | `presentation/cli/ping` |
| `monitor.ping.finished` | INFO | `presentation/cli/ping` (contagens reachable/unreachable/updated/unchanged) |
| `monitor.ping.failed` | WARNING/ERROR | probe/set_enabled por servidor (WARNING); falha do execute (ERROR) |

Caminho feliz com um alerta novo no primeiro ciclo (~4 INFO apos o boot): `started` → `sink.published` (`alerts_count=1`) → `gchat.published` (`alerts_count=1`) → `finished`. Com N claimed e ledger ligado: N pares `sink.published` / `gchat.published`, cada um com `alerts_count=1`.
Ciclo ocioso depois do heartbeat: silencio (sem `started`/`finished`). Alerta novo depois do primeiro ciclo: `published` → `finished` (sem `started`).
Ciclo sobreposto: `skipped_in_flight` (sem `started`).
Fail-open de fetch/config/som: WARNING e o ciclo segue. Falha de Chat: WARNING, release do fingerprint, ciclo segue.

## Variaveis

| Env | Default | Descricao |
|-----|---------|-----------|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL` |
| `LOG_FORMAT` | `text` | `text` (key=value) ou `json` |
| `LOG_FILE` | vazio | Se definido, tambem grava eventos semanticos nesse arquivo (flush a cada emit) |
| `LOG_DIR` | `logs` | Tee de stdout/stderr em `LOG_DIR/nagstamon-YYYY-MM-DD.log` (fuso `WINDOW_TIMEZONE`); omite WARNING/ERROR/DEBUG/CRITICAL semanticos (igual `make docker-logs`). Vazio desliga. No Docker o compose monta `logs/` do host em `/var/log/nagstamon-headless`. `make app-clean` remove arquivos em `logs/` que nao sejam o do dia atual nem `.gitkeep` |

Setup: `presentation.logging.setup_logging(...)`.

## Anti-poluicao

- Dominio nao loga.
- Use case nao loga.
- `httpx` / `httpcore` / `urllib3` em `WARNING`.
- Query string redigida (`redact_url` → `?***`).
- Campo logado como `monitor_host` (URL sem query secreta).
- Sem dump de body HTTP ou lista de alertas em INFO.
- `exc_info` so quando `LOG_LEVEL=DEBUG` em falhas de ciclo/fetch/Chat.
- `monitor.config.empty` nao se repete a cada poll; `finished` ja leva `servers_count`.
- Dedup nao emite evento extra: `finished` ja leva `skipped_duplicate_count`.
- Ciclo ocioso nao emite `started`/`finished`; o primeiro ciclo e o heartbeat.
- Webhook do Chat: query redigida em `webhook_host`.

## Exemplo (text)

```text
2026-08-13 12:00:00,000 INFO event=worker.started refresh_interval=30 dedup_enabled=True dedup_window_minutes=30 log_format=text
2026-08-13 12:00:00,001 INFO event=poll.cycle.started
2026-08-13 12:00:00,050 INFO event=poll.sink.published alerts_count=1
2026-08-13 12:00:00,051 INFO event=poll.gchat.published alerts_count=1
2026-08-13 12:00:00,052 INFO event=poll.sink.published alerts_count=1
2026-08-13 12:00:00,053 INFO event=poll.gchat.published alerts_count=1
2026-08-13 12:00:00,054 INFO event=poll.sink.published alerts_count=1
2026-08-13 12:00:00,055 INFO event=poll.gchat.published alerts_count=1
2026-08-13 12:00:00,056 INFO event=poll.cycle.finished status=ok servers_count=2 alerts_count=3 claimed_count=3 skipped_duplicate_count=0 duration_ms=55
```

## Exemplo (WARNING)

```text
2026-08-13 12:00:00,000 INFO event=worker.started refresh_interval=30 dedup_enabled=True dedup_window_minutes=30 log_format=text
2026-08-13 12:00:00,001 INFO event=poll.cycle.started
2026-08-13 12:00:00,020 WARNING event=monitor.fetch.failed server_name=am monitor_host=http://am.example error_type=http_status http_status=500
2026-08-13 12:00:00,021 WARNING event=monitor.config.empty servers_count=0
2026-08-13 12:00:00,022 WARNING event=poll.sound.failed error_type=missing_player
2026-08-13 12:00:00,023 WARNING event=poll.gchat.failed error_type=http_status http_status=500 webhook_host=https://chat.googleapis.com/v1/spaces/AAA/messages?***
2026-08-13 12:00:00,024 INFO event=poll.cycle.finished status=ok servers_count=0 alerts_count=0 claimed_count=0 skipped_duplicate_count=0 duration_ms=21
```
