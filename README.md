# Nagstamon Headless

[![CI](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/actions/workflows/ci.yml/badge.svg)](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/victorhc-silveira-ilegra/nagstamon-headless?display_name=tag&sort=semver)](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](app/pyproject.toml)
[![Ruff](https://img.shields.io/badge/linter-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/)
[![Semantic Release](https://img.shields.io/badge/release-semantic--release-e10079?logo=semantic-release&logoColor=white)](https://semantic-release.gitbook.io/)
[![Architecture](https://img.shields.io/badge/architecture-hexagonal%20%2F%20DDD-0A66C2)](docs/arquitetura.md)

Daemon headless que consulta monitores (Prometheus Alertmanager e Nagios CGI), aplica os filtros de ruido no estilo Nagstamon e imprime os **alertas efetivos** no stdout (Client, Host, Service, Status, Duration, Started, Status information). Google Chat e opcional (`GCHAT_WEBHOOK_URL`); despacho idempotente via ledger em `DEDUP_LEDGER_PATH`.

Arquitetura: DDD / hexagonal. Qualidade: Ruff, mypy strict, vulture, pytest com cobertura 100% (branch), bandit e pip-audit.

## Setup

```bash
cp .env.example .env
make app-setup
```

Ajuste `.env` (proxy, VPN, diretorio de `.conf`, intervalo). Credenciais ficam nos arquivos `~/.nagstamon/servers/*.conf` (ofuscadas pelo GUI); o daemon desofusca como o Nagstamon. `make docker-smoke` usa essa config real (VPN + proxy + `*.conf`); nao roda com servers vazios.

`make app-setup` instala `.venv` e dependencias. Hooks git so sao instalados se o diretorio ja for um repositorio git.

## Comandos

```bash
make app-lint
make app-test
make app-security
make app-run
make docker-up
make docker-smoke
make docker-logs
```

O orquestrador unico e `app/scripts/operations/clean_workspace.py`.

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml):

- jobs paralelos: lint, test, security (actions compostas)
- job `release` (semantic-release) apos qualidade em `main`
- tags sincronizadas via `.github/actions/sync-tags`
- changelog em [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

## Documentacao

- [docs/CHANGELOG.md](docs/CHANGELOG.md)
- [docs/arquitetura.md](docs/arquitetura.md)
- [docs/structure.md](docs/structure.md)
- [docs/engineering-python.md](docs/engineering-python.md)
- [docs/engineering-logging.md](docs/engineering-logging.md)
- [docs/infra-docker.md](docs/infra-docker.md)
- [AGENTS.md](AGENTS.md)
- [prompt-model.md](prompt-model.md)
