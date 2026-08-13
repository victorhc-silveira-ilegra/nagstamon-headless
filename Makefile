SHELL := /bin/bash
APP_DIR=app
DOCKER_DIR=infra/docker
DOCKER_COMPOSE=docker compose --env-file .env -f $(DOCKER_DIR)/docker-compose.yml --project-directory $(DOCKER_DIR)
DOCKER_LOGS_TAIL ?= 200
DOCKER_LOGS_SERVICES ?= nagstamon-headless

RESOLVE_PY := $(shell bash linters/git-hooks/bin/resolve_venv_python.sh 2>/dev/null || echo python3)
PYTHON := $(RESOLVE_PY)

GREEN  := \033[1;32m
YELLOW := \033[1;33m
BLUE   := \033[1;34m
CYAN   := \033[1;36m
RED    := \033[1;31m
RESET  := \033[0m

.DEFAULT_GOAL := help

.PHONY: help app-install app-lint app-test app-security app-run app-pre-commit \
	app-pre-commit-run app-setup app-clean docker-up docker-down docker-ps \
	docker-logs docker-sh docker-restart docker-clean docker-rebuild

help:
	@echo -e "$(BLUE)========================================================================$(RESET)"
	@echo -e "$(GREEN)              NAGSTAMON HEADLESS - MENU DE AJUDA                        $(RESET)"
	@echo -e "$(BLUE)========================================================================$(RESET)"
	@echo -e "Uso: $(CYAN)make <comando>$(RESET)"
	@echo -e ""
	@echo -e "$(YELLOW)Python:$(RESET) $(PYTHON)"
	@echo -e ""
	@echo -e "$(YELLOW)App:$(RESET)"
	@echo -e "  $(GREEN)app-run$(RESET)            - Executa o daemon local"
	@echo -e "  $(GREEN)app-test$(RESET)           - Testes + cobertura 100%"
	@echo -e "  $(GREEN)app-lint$(RESET)           - Lint / format / mypy / vulture"
	@echo -e "  $(GREEN)app-security$(RESET)       - Bandit + pip-audit"
	@echo -e "  $(GREEN)app-clean$(RESET)          - Limpa caches/logs locais"
	@echo -e "  $(GREEN)app-install$(RESET)        - Pip no .venv"
	@echo -e "  $(GREEN)app-setup$(RESET)          - Bootstrap .venv + deps (+ hooks se houver git)"
	@echo -e "  $(GREEN)app-pre-commit$(RESET)     - Instala hooks no Git"
	@echo -e "  $(GREEN)app-pre-commit-run$(RESET) - Roda hooks em todos os arquivos"
	@echo -e ""
	@echo -e "$(YELLOW)Docker:$(RESET)"
	@echo -e "  $(GREEN)docker-up$(RESET)          - Sobe o daemon headless"
	@echo -e "  $(GREEN)docker-rebuild$(RESET)     - Rebuild da imagem e recria o container"
	@echo -e "  $(GREEN)docker-down$(RESET)        - Para o container (preserva volumes)"
	@echo -e "  $(GREEN)docker-clean$(RESET)       - $(RED)DESTRUTIVO$(RESET): remove containers, redes e volumes"
	@echo -e "  $(GREEN)docker-restart$(RESET)     - Restart do servico"
	@echo -e "  $(GREEN)docker-ps$(RESET)          - Status"
	@echo -e "  $(GREEN)docker-logs$(RESET)        - Logs (DOCKER_SERVICE=...; F=1 para follow)"
	@echo -e "  $(GREEN)docker-sh$(RESET)          - Shell /bin/bash no container"
	@echo -e "$(BLUE)========================================================================$(RESET)"

app-install:
	@test -d .venv || python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r $(APP_DIR)/requirements.txt -r $(APP_DIR)/requirements-dev.txt
	$(PYTHON) -m pip install -e $(APP_DIR)

app-lint:
	$(PYTHON) $(APP_DIR)/scripts/operations/clean_workspace.py --stage lint

app-test:
	$(PYTHON) $(APP_DIR)/scripts/operations/clean_workspace.py --stage test

app-security:
	$(PYTHON) $(APP_DIR)/scripts/operations/clean_workspace.py --stage security

app-run:
	$(PYTHON) run.py

app-pre-commit:
	bash linters/git-hooks/install.sh
	chmod +x linters/git-hooks/bin/resolve_venv_python.sh linters/git-hooks/bin/python linters/git-hooks/bin/pre-commit

app-pre-commit-run:
	$(PYTHON) -m pre_commit run --all-files -c .pre-commit-config.yaml

app-setup:
	bash app/scripts/setup.sh

app-clean:
	$(PYTHON) $(APP_DIR)/scripts/operations/clean_workspace.py --stage clean

docker-up:
	@test -f .env || cp .env.example .env
	$(DOCKER_COMPOSE) up -d --build

docker-rebuild:
	@test -f .env || cp .env.example .env
	@echo -e "$(YELLOW)Rebuild da imagem e recriacao do container$(RESET)"
	$(DOCKER_COMPOSE) build --pull
	$(DOCKER_COMPOSE) up -d --force-recreate --remove-orphans
	@$(DOCKER_COMPOSE) ps

docker-down:
	$(DOCKER_COMPOSE) down

docker-clean:
	@test -f .env || cp .env.example .env
	@echo -e "$(RED)Removendo containers, redes e volumes$(RESET)"
	$(DOCKER_COMPOSE) down --volumes --remove-orphans --rmi local
	@$(DOCKER_COMPOSE) ps

docker-restart:
	@test -f .env || cp .env.example .env
	$(DOCKER_COMPOSE) restart

docker-ps:
	$(DOCKER_COMPOSE) ps

docker-logs:
	$(DOCKER_COMPOSE) logs --timestamps --tail=$(DOCKER_LOGS_TAIL) $(if $(F),-f,) $(if $(DOCKER_SERVICE),$(DOCKER_SERVICE),$(DOCKER_LOGS_SERVICES))

docker-sh:
	@echo -e "$(CYAN)Abrindo /bin/bash em '$(or $(DOCKER_SERVICE),nagstamon-headless)'$(RESET)"
	$(DOCKER_COMPOSE) exec $(or $(DOCKER_SERVICE),nagstamon-headless) /bin/bash
