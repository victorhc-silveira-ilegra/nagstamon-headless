# AGENTS.md

Projeto: Nagstamon Headless (DDD / Hexagonal) — polling de Alertmanager e Nagios CGI com filtros de alertas efetivos.

## Prioridades

1. Preservar camadas em `app/src` (`domain`, `application`, `infrastructure`, `presentation`).
2. Usar `make app-lint|app-test|app-security` (via `clean_workspace.py`) apos mudancas. CI em `.github/workflows/ci.yml`.
3. Nao escrever comentarios no codigo.
4. Manter cobertura 100% e Conventional Commits.
5. Config via `.env` na raiz (`SERVERS_DIR`, `PROXY_ADDR`, `REFRESH_INTERVAL`, `HTTP_*`, `DEDUP_*`, `LOG_*`).
6. Manter docs em `docs/` alinhadas ao codigo (arquitetura, structure, engineering-*).
7. Logs semanticos: INFO no caminho feliz, WARNING em fail-open/overlap, ERROR so em boot ou ciclo quebrado. Dominio e use case nao logam.

## Comandos uteis

```bash
make app-install
make app-lint
make app-test
make docker-up
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
- Encaminhamento para Google Chat, OTRS ou outras sinks alem do stdout
