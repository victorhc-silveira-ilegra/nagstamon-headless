# Arquitetura do Nagstamon Headless

## Visao geral

Daemon Python em arquitetura **hexagonal / DDD**: regras de filtragem e entidades ficam isoladas de HTTP, arquivos INI e stdout. O worker na presentation e o composition root.

```text
~/.nagstamon/servers/*.conf
        |
        v
IniServerConfigAdapter
        |
        v
presentation/worker  (composition root)
        |
        v
PollMonitorsUseCase   (application)
   |            |                |              |              |
   v            v                v              v              v
ServerConfig   MonitorClient   AlertSink   AlertDispatch   AlertSound
Port           Port            Port        LedgerPort      Port
                  |                |              |              |
                  v                v              v              v
         CompositeMonitorClient  Composite   File/InMemory    PopenAlertSound
           |              |      AlertSink   Ledger
           v              v        |     \
   AlertmanagerHttp   NagiosCgiHttp |      \
                                   v       v
                             Stdout     GoogleChatWebhook
```

## Camadas

### Domain (`app/src/domain`)

| Modulo | Papel |
|--------|--------|
| `entities/monitor_server.py` | Servidor de monitor: URL, proxy, credenciais, tipo, `enabled` |
| `entities/alert.py` | Alerta efetivo candidato; `host`; `acknowledged`; `dedup_key()` do problema (`server`/`alertname`/`app`/`host`, sem `desc` dinamico nem `starts_at`) |
| `entities/severity.py` | Severidade normalizada |
| `services/alert_filter.py` | Politica de ruido (ack, hold-down, janela, dias uteis, Watchdog, Kubernetes, silenced/inhibited) |
| `services/alert_hold.py` | Criticidade de persistencia: muito critico (10 min) / mediano (15 min) / baixo (20 min); INFO fora |
| `services/alert_view.py` | Snapshot texto enriquecido: Status, Client, Host, Service, Ambiente, Duração no Nagstamon, Horário do envio, Início do alarme, Status information e métricas SLA/SLO (Criticidade SLA, Tempo decorrido, ID do Incidente) |

O dominio **nao** loga e **nao** conhece httpx nem `.env`.

### Application (`app/src/application`)

| Modulo | Papel |
|--------|--------|
| `ports/server_config.py` | `list_enabled()` / `list_all()` / `set_enabled(name, enabled)` |
| `ports/monitor_client.py` | `fetch_all(servers)` |
| `ports/monitor_probe.py` | `probe(server) -> bool` (HTTP 2xx) |
| `ports/alert_sink.py` | `publish(alerts, fetched_at=...)` (stdout e Google Chat) |
| `ports/clock.py` | Relogio injetavel |
| `ports/alert_dispatch_ledger.py` | `try_claim` / `confirm` / `release` (dedup persistente) |
| `ports/alert_sound.py` | `play_new_alert()` apos publish de alerta claimed |
| `use_cases/poll_monitors.py` | Um ciclo: fetch → filtro → unique → claim/publish/confirm por alerta → som |
| `use_cases/ping_monitors.py` | One-shot: `list_all` → probe paralelo → `set_enabled` conforme 2xx |

O use case **nao** loga. Paralelismo HTTP fica no adapter composto (poll) ou no use case de ping.

### Infrastructure (`app/src/infrastructure`)

| Modulo | Papel |
|--------|--------|
| `config/settings.py` | `Settings.from_env()` |
| `config/dotenv_loader.py` | Carrega `.env` da raiz |
| `adapters/ini_server_config.py` | Parser INI estilo Nagstamon; `list_enabled` / `list_all` / `set_enabled` (so a linha `enabled=`); desofusca username/password |
| `adapters/alertmanager_http.py` | GET `/api/v2/alerts` via httpx |
| `adapters/nagios_cgi_http.py` | GET CGI HTML (tabelas aninhadas); host/service/duracao/ack |
| `adapters/http_monitor_probe.py` | Probe HTTP autenticado (AM/Nagios); tipos fora de escopo = False |
| `adapters/composite_monitor_client.py` | Roteia AM vs Nagios em ThreadPoolExecutor |
| `adapters/stdout_alert_sink.py` | Snapshot de alertas efetivos no stdout (fuso injetado) |
| `adapters/google_chat_http.py` | POST da mesma mensagem `text` no webhook; loga `poll.gchat.failed` e raises para o use case dar release |
| `adapters/composite_alert_sink.py` | Encadeia stdout e Google Chat no mesmo `publish` |
| `adapters/in_memory_alert_dispatch_ledger.py` | Dedup com `threading.Lock` quando `DEDUP_LEDGER_PATH` vazio |
| `adapters/file_alert_dispatch_ledger.py` | JSON + `fcntl.flock`; pending/sent; sobrevive a restart |
| `adapters/popen_alert_sound.py` | Beep WAV via `paplay`/`aplay`; fail-open (`poll.sound.failed`) |
| `logging/*` | `log_event`, eventos, redact |

Falha de IO por servidor e fail-open: lista vazia + `monitor.fetch.failed` (WARNING).
Falha do player de som e fail-open: `poll.sound.failed` (WARNING); o ciclo segue.
Falha do Google Chat: `poll.gchat.failed` (WARNING), o use case libera o fingerprint e o ciclo segue.
Boot: `worker.started`; config invalida: `worker.boot.failed` (ERROR).
Overlap de ciclo: `poll.cycle.skipped_in_flight` (WARNING).

### Presentation (`app/src/presentation`)

| Modulo | Papel |
|--------|--------|
| `worker/main.py` | Composition root + loop do daemon |
| `worker/cycle_guard.py` | Trava in-flight: um ciclo por vez no processo |
| `cli/ping.py` | Composition root one-shot: probe HTTP e grava `enabled` (`HOST_SERVERS_DIR` se existir) |
| `logging/*` | Setup root logger (`text` / `json`), tee diario em `LOG_DIR`, silence httpx |

CLI do daemon: `--max-cycles` (opcional; omitido = loop infinito). Ping: `make app-ping` / `nagstamon-headless-ping` (sem args).

## Config

Variaveis no `.env` da raiz. Testes isolam com `NAGSTAMON_DISABLE_DOTENV=1`.

Dedup: `DEDUP_ENABLED` (default true), `DEDUP_WINDOW_MINUTES` (mantido na env; fingerprints `sent` nao expiram) e `DEDUP_LEDGER_PATH` (vazio = memoria; arquivo JSON com flock). O mesmo alerta/problema (server/alertname/app/host) e emitido uma vez ate `release` (falha de Chat) ou apagar o ledger, mesmo que a descricao ou metricas dinamicas (KB de memoria, latencia HTTP, duracao) variem nos ciclos subsequentes. `DEDUP_ENABLED=false` republica o snapshot a cada ciclo.

Filtros de janela: `WINDOW_ENABLED` (default true), `WINDOW_START` (default `13:30`), `WINDOW_END` (default `18:00`), `WINDOW_DAYS` (default `mon,tue,wed,thu,fri`; aceita `seg..dom` ou `0..6`), `WINDOW_TIMEZONE` (default `America/Sao_Paulo`), `WINDOW_ALLOW_PAST_ACTIVE_ALERTS` (default true no turno da manha `WINDOW_START < 12:00`, false na tarde) e `FILTER_DURATION_MAX_SECONDS` (default 86400). Inclusivo nos extremos da janela. Com a janela ligada, `now` precisa estar no horario **e** em um dia util configurado; se o inicio do alerta for conhecido, precisa cair no mesmo intervalo hoje ou antes dele quando `WINDOW_ALLOW_PAST_ACTIVE_ALERTS=true` (permitindo que alertas ativos iniciados na madrugada ou antes do boot sejam despachados no primeiro ciclo da manha). `WINDOW_ENABLED=false` ignora horario e dia. Sem inicio conhecido ou INFO: nao dispara. Duracao e horario sao calculados em Python.

Hold-down por criticidade (tipo ganha de severidade; keywords so em alertname/desc/status, nao no host):

| Criticidade | Quem | Env | Default |
|-------------|------|-----|---------|
| Muito critico | DOWN/unreachable, disco/filesystem, cert/TLS, pagamento/login | `FILTER_HOLD_FAST_SECONDS` | 600 (10 min) |
| Mediano | CRITICAL restante | `FILTER_HOLD_CRITICAL_SECONDS` | 900 (15 min) |
| Baixo | WARNING restante e CPU/mem/load/fila/lock/ping/latencia/flap | `FILTER_HOLD_WARNING_SECONDS` | 1200 (20 min) |

Som: `SOUND_ENABLED` (default true). Toca apos `confirm` de pelo menos um alerta (ou lista nao vazia com dedup off). Compose forca `false` (container sem Pulse).

Google Chat: `GCHAT_WEBHOOK_URL` (vazio = desligado). Com ledger, um alerta claimed por `publish([alert])`; o mesmo texto do stdout vai ao webhook como mensagem `{"text": ...}` (sem cards estruturados do Chat e sem fence monoespaçado). Falha loga e raises; o use case libera o fingerprint. Token fica so no `.env` local; logs redigem a query.

Arquivo diario: `LOG_DIR` (default `logs`; vazio desliga). O worker faz tee de stdout/stderr para `LOG_DIR/nagstamon-YYYY-MM-DD.log` no fuso `WINDOW_TIMEZONE`, com o mesmo recorte do `make docker-logs` (INFO + snapshot). No Docker o volume `logs/` do host aponta para `/var/log/nagstamon-headless`. `make app-clean` apaga em `logs/` o que nao for o arquivo do dia atual nem `.gitkeep`. `LOG_FILE` continua opcional para um arquivo extra so de eventos semanticos.
