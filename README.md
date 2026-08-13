# Nagstamon Headless

[![CI](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/actions/workflows/ci.yml/badge.svg)](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/victorhc-silveira-ilegra/nagstamon-headless?display_name=tag&sort=semver)](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Requires Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fvictorhc-silveira-ilegra%2Fnagstamon-headless%2Fmain%2Fapp%2Fpyproject.toml)](app/pyproject.toml)
[![CI Python](https://img.shields.io/badge/CI-Python%203.13.12-3776AB?logo=python&logoColor=white)](.github/workflows/ci.yml)
[![GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)
[![Last commit](https://img.shields.io/github/last-commit/victorhc-silveira-ilegra/nagstamon-headless)](https://github.com/victorhc-silveira-ilegra/nagstamon-headless/commits/main)

[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](app/pyproject.toml)
[![Branch coverage](https://img.shields.io/badge/branch%20coverage-100%25-brightgreen)](app/pyproject.toml)
[![pytest](https://img.shields.io/badge/pytest-9-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![pytest-cov](https://img.shields.io/badge/pytest--cov-enabled-0A9EDC)](https://pytest-cov.readthedocs.io/)
[![pytest-xdist](https://img.shields.io/badge/pytest--xdist-parallel-0A9EDC)](https://pytest-xdist.readthedocs.io/)
[![coverage.py](https://img.shields.io/badge/coverage.py-branch-green)](https://coverage.readthedocs.io/)
[![TDD](https://img.shields.io/badge/tests-TDD%20%2B%20pytest-0A9EDC?logo=pytest&logoColor=white)](docs/engineering-python.md)

[![Ruff](https://img.shields.io/badge/linter-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Ruff Format](https://img.shields.io/badge/formatter-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![Typed](https://img.shields.io/badge/typing-strict-blue)](app/pyproject.toml)
[![vulture](https://img.shields.io/badge/dead%20code-vulture-orange)](https://github.com/jendrikseipp/vulture)
[![Line limit](https://img.shields.io/badge/max%20lines-300-lightgrey)](app/scripts/operations/clean_workspace.py)

[![bandit](https://img.shields.io/badge/security-bandit-yellow)](https://bandit.readthedocs.io/)
[![pip-audit](https://img.shields.io/badge/deps-pip--audit-informational)](https://pypi.org/project/pip-audit/)
[![gitleaks](https://img.shields.io/badge/secrets-gitleaks-1E2327)](https://github.com/gitleaks/gitleaks)
[![Pinned deps](https://img.shields.io/badge/deps-pinned-informational)](app/requirements.txt)

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![commitlint](https://img.shields.io/badge/commitlint-enabled-121212?logo=commitlint&logoColor=white)](https://commitlint.js.org/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/)
[![Semantic Release](https://img.shields.io/badge/release-semantic--release-e10079?logo=semantic-release&logoColor=white)](https://semantic-release.gitbook.io/)
[![SemVer](https://img.shields.io/badge/semver-2.0.0-blue)](https://semver.org/)

[![Architecture](https://img.shields.io/badge/architecture-hexagonal%20%2F%20DDD-0A66C2)](docs/arquitetura.md)
[![Clean Architecture](https://img.shields.io/badge/ports%20%26%20adapters-hexagonal-0A66C2)](docs/arquitetura.md)
[![Logging](https://img.shields.io/badge/logging-semantic%20INFO%2FWARNING%2FERROR-informational)](docs/engineering-logging.md)
[![Make](https://img.shields.io/badge/build-Make-000000?logo=gnu&logoColor=white)](Makefile)
[![setuptools](https://img.shields.io/badge/packaging-setuptools-3776AB?logo=pypi&logoColor=white)](app/pyproject.toml)
[![httpx](https://img.shields.io/badge/http-httpx-0052CC)](https://www.python-httpx.org/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](docs/infra-docker.md)
[![Linux](https://img.shields.io/badge/os-Linux-FCC624?logo=linux&logoColor=black)](https://www.linux.org/)

[![Alertmanager](https://img.shields.io/badge/Prometheus-Alertmanager-E6522C?logo=prometheus&logoColor=white)](docs/arquitetura.md)
[![Nagios](https://img.shields.io/badge/Nagios-CGI-A4C639)](docs/arquitetura.md)
[![License](https://img.shields.io/badge/license-Proprietary-lightgrey)](app/pyproject.toml)

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
