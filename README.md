# Nagstamon Headless

Daemon headless que consulta monitores (Prometheus Alertmanager e Nagios CGI), aplica os filtros de ruido no estilo Nagstamon e imprime os **alertas efetivos** no stdout.

Arquitetura: DDD / hexagonal. Qualidade: Ruff, mypy strict, vulture, pytest com cobertura 100% (branch), bandit e pip-audit.

## Setup

```bash
cp .env.example .env
make app-setup
```

Ajuste `.env` (proxy, diretorio de `.conf`, intervalo). Credenciais ficam nos arquivos `~/.nagstamon/servers/*.conf`, nao no git.

`make app-setup` instala `.venv` e dependencias. Hooks git so sao instalados se o diretorio ja for um repositorio git.

## Comandos

```bash
make app-lint
make app-test
make app-security
make app-run
make docker-up
make docker-logs
```

O orquestrador unico e `app/scripts/operations/clean_workspace.py`.

## Documentacao

- [docs/arquitetura.md](docs/arquitetura.md)
- [docs/structure.md](docs/structure.md)
- [docs/engineering-python.md](docs/engineering-python.md)
- [docs/engineering-logging.md](docs/engineering-logging.md)
- [docs/infra-docker.md](docs/infra-docker.md)
- [AGENTS.md](AGENTS.md)
- [prompt-model.md](prompt-model.md)
