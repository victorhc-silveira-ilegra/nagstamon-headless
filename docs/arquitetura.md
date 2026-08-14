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
| `entities/monitor_server.py` | Servidor de monitor: URL, proxy, credenciais, tipo |
| `entities/alert.py` | Alerta efetivo candidato; `host`; `acknowledged`; `dedup_key()` com host, sem `starts_at` |
| `entities/severity.py` | Severidade normalizada |
| `services/alert_filter.py` | Politica de ruido (ack, hold-down por criticidade, janela, Watchdog, silenced/inhibited) |
| `services/alert_hold.py` | Criticidade de persistencia: muito critico (10 min) / mediano (15 min) / baixo (20 min); INFO fora |
| `services/alert_view.py` | Snapshot texto: Client, Host, Service, Status, Duration, Started, Status information |

O dominio **nao** loga e **nao** conhece httpx nem `.env`.

### Application (`app/src/application`)

| Modulo | Papel |
|--------|--------|
| `ports/server_config.py` | `list_enabled()` |
| `ports/monitor_client.py` | `fetch_all(servers)` |
| `ports/alert_sink.py` | `publish(alerts, fetched_at=...)` (stdout e Google Chat) |
| `ports/clock.py` | Relogio injetavel |
| `ports/alert_dispatch_ledger.py` | `try_claim` / `confirm` / `release` (dedup persistente) |
| `ports/alert_sound.py` | `play_new_alert()` apos publish de alerta claimed |
| `use_cases/poll_monitors.py` | Um ciclo: fetch → filtro → unique → claim/publish/confirm por alerta → som |

O use case **nao** loga. Paralelismo HTTP fica no adapter composto.

### Infrastructure (`app/src/infrastructure`)

| Modulo | Papel |
|--------|--------|
| `config/settings.py` | `Settings.from_env()` |
| `config/dotenv_loader.py` | Carrega `.env` da raiz |
| `adapters/ini_server_config.py` | Parser INI estilo Nagstamon; desofusca username/password |
| `adapters/alertmanager_http.py` | GET `/api/v2/alerts` via httpx |
| `adapters/nagios_cgi_http.py` | GET CGI HTML (tabelas aninhadas); host/service/duracao/ack |
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
| `logging/*` | Setup root logger (`text` / `json`), silence httpx |

CLI: `--max-cycles` (opcional; omitido = loop infinito).

## Config

Variaveis no `.env` da raiz. Testes isolam com `NAGSTAMON_DISABLE_DOTENV=1`.

Dedup: `DEDUP_ENABLED` (default true), `DEDUP_WINDOW_MINUTES` (default 30) e `DEDUP_LEDGER_PATH` (vazio = memoria; arquivo JSON com flock). `DEDUP_ENABLED=false` republica o snapshot a cada ciclo.

Filtros de janela: `FILTER_WINDOW_START` (default `13:30`), `FILTER_WINDOW_END` (default `18:00`), `FILTER_TIMEZONE` (default `America/Sao_Paulo`) e `FILTER_DURATION_MAX_SECONDS` (default 86400). Inclusivo nos extremos da janela. `now` precisa estar nela; se o inicio do alerta for conhecido, tambem precisa cair no mesmo intervalo hoje. Inicio conhecido anterior ao boot do processo nao dispara stdout/Chat. Sem inicio conhecido ou INFO: nao dispara. Duracao e horario sao calculados em Python.

Hold-down por criticidade (tipo ganha de severidade; keywords so em alertname/desc/status, nao no host):

| Criticidade | Quem | Env | Default |
|-------------|------|-----|---------|
| Muito critico | DOWN/unreachable, disco/filesystem, cert/TLS, pagamento/login | `FILTER_HOLD_FAST_SECONDS` | 600 (10 min) |
| Mediano | CRITICAL restante | `FILTER_HOLD_CRITICAL_SECONDS` | 900 (15 min) |
| Baixo | WARNING restante e CPU/mem/load/fila/lock/ping/latencia/flap | `FILTER_HOLD_WARNING_SECONDS` | 1200 (20 min) |

Som: `SOUND_ENABLED` (default true). Toca apos `confirm` de pelo menos um alerta (ou lista nao vazia com dedup off). Compose forca `false` (container sem Pulse).

Google Chat: `GCHAT_WEBHOOK_URL` (vazio = desligado). Com ledger, um alerta claimed por `publish([alert])`; o mesmo texto do stdout vai ao webhook como mensagem `{"text": ...}` (sem cards estruturados do Chat e sem fence monoespaçado). Falha loga e raises; o use case libera o fingerprint. Token fica so no `.env` local; logs redigem a query.
