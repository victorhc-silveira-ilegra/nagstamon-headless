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
   |            |                |              |
   v            v                v              v
ServerConfig   MonitorClient   AlertSink   AlertDispatchLedger
Port           Port            Port        Port
                  |                |              |
                  v                v              v
         CompositeMonitorClient  Stdout     InMemoryAlertDispatchLedger
           |              |
           v              v
   AlertmanagerHttp   NagiosCgiHttp
```

## Camadas

### Domain (`app/src/domain`)

| Modulo | Papel |
|--------|--------|
| `entities/monitor_server.py` | Servidor de monitor: URL, proxy, credenciais, tipo |
| `entities/alert.py` | Alerta efetivo candidato; `dedup_key()` sem `starts_at` |
| `entities/severity.py` | Severidade normalizada |
| `services/alert_filter.py` | Politica de ruido (texto, duracao, Watchdog, silenced/inhibited) |

O dominio **nao** loga e **nao** conhece httpx nem `.env`.

### Application (`app/src/application`)

| Modulo | Papel |
|--------|--------|
| `ports/server_config.py` | `list_enabled()` |
| `ports/monitor_client.py` | `fetch_all(servers)` |
| `ports/alert_sink.py` | `publish(alerts, fetched_at=...)` |
| `ports/clock.py` | Relogio injetavel |
| `ports/alert_dispatch_ledger.py` | `try_claim` / `release` (dedup in-memory) |
| `use_cases/poll_monitors.py` | Um ciclo: fetch → filtro → unique/claim → sink |

O use case **nao** loga. Paralelismo HTTP fica no adapter composto.

### Infrastructure (`app/src/infrastructure`)

| Modulo | Papel |
|--------|--------|
| `config/settings.py` | `Settings.from_env()` |
| `config/dotenv_loader.py` | Carrega `.env` da raiz |
| `adapters/ini_server_config.py` | Parser INI estilo Nagstamon |
| `adapters/alertmanager_http.py` | GET `/api/v2/alerts` via httpx |
| `adapters/nagios_cgi_http.py` | GET CGI HTML + regex (comportamento legado) |
| `adapters/composite_monitor_client.py` | Roteia AM vs Nagios em ThreadPoolExecutor |
| `adapters/stdout_alert_sink.py` | Lista de alertas efetivos no stdout |
| `adapters/in_memory_alert_dispatch_ledger.py` | Dedup com `threading.Lock` (perde no restart) |
| `logging/*` | `log_event`, eventos, redact |

Falha de IO por servidor e fail-open: lista vazia + `monitor.fetch.failed` (WARNING).
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

Dedup: `DEDUP_ENABLED` (default true) e `DEDUP_WINDOW_MINUTES` (default 30). Ledger so em memoria; `DEDUP_ENABLED=false` republica o snapshot a cada ciclo.
