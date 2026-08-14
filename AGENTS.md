# AGENTS.md

Projeto: Nagstamon Headless (DDD / Hexagonal) — polling de Alertmanager e Nagios CGI com filtros de alertas efetivos.

## Prioridades

1. Preservar camadas em `app/src` (`domain`, `application`, `infrastructure`, `presentation`).
2. Usar `make app-lint|app-test|app-security` (via `clean_workspace.py`) apos mudancas. CI em `.github/workflows/ci.yml`.
3. Nao escrever comentarios no codigo.
4. Manter cobertura 100% e Conventional Commits.
5. Config via `.env` na raiz (`SERVERS_DIR`, `PROXY_ADDR`, `VPN_*`, `REFRESH_INTERVAL`, `HTTP_*`, `DEDUP_*`, `FILTER_*`, `SOUND_*`, `GCHAT_*`, `LOG_*`). Proxy/VPN reais e webhook do Chat so no `.env` local.
6. Manter docs em `docs/` alinhadas ao codigo (arquitetura, structure, engineering-*).
7. Logs semanticos: INFO no caminho feliz (boot, primeiro ciclo, publish), WARNING em fail-open/overlap, ERROR so em boot ou ciclo quebrado. Dominio e use case nao logam. Ciclo ocioso nao emite started/finished.
8. Snapshot no stdout e no Google Chat: mesmo texto (Client, Host, Service, Status, Duration, Started, Status information em `domain/services/alert_view.py`); Chat via mensagem `text` (nao card estruturado); dedup persistente por fingerprint (inclui host) via ledger claim/confirm/release.
9. Filtro de data/horario/intervalo so em Python (`starts_at` ou parse de `duration_str`); sem regex da aba Filters do GUI. Hold-down por criticidade: muito critico 10 min (`FILTER_HOLD_FAST_SECONDS`), mediano 15 min (`FILTER_HOLD_CRITICAL_SECONDS`), baixo 20 min (`FILTER_HOLD_WARNING_SECONDS`); tipo ganha de severidade; INFO nao dispara. Alerta sem inicio conhecido ou com inicio anterior ao boot nao entra no snapshot.

## Comandos uteis

```bash
make app-install
make app-lint
make app-test
make docker-up
make docker-smoke
```

## Prompt-modelo

- [prompt-model.md](prompt-model.md) — contrato reutilizavel (DDD / hexagonal / TDD / qualidade) para colar em projetos futuros e adaptar a outra linguagem ou dominio

## Docs de referencia

- [docs/arquitetura.md](docs/arquitetura.md)
- [docs/engineering-python.md](docs/engineering-python.md)
- [docs/engineering-logging.md](docs/engineering-logging.md)
- [docs/structure.md](docs/structure.md)
- [docs/infra-docker.md](docs/infra-docker.md)

## Fora de escopo

- UI desktop Qt do Nagstamon original
- Icinga / Centreon / Checkmk / Zabbix nativos
- Encaminhamento para OTRS ou outras sinks alem de stdout e Google Chat
