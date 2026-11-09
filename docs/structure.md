# Estrutura do Repositório

Este documento descreve a topologia de diretórios, convenções de empacotamento e regras de isolamento arquitetural do **Nagstamon Headless**.

## 1. Topologia de Diretórios

```text
.
├── .agents/                               # Harness universal para LLMs e agentes autônomos
│   ├── README.md                          # Manifesto e governança do harness
│   ├── rules/                             # Regras de engenharia, DDD, SLA e observabilidade
│   └── skills/                            # Habilidades e procedimentos operacionais
├── .github/                               # Governança de CI/CD e automações GitHub
│   ├── README.md                          # Índice das ações e fluxos de automação
│   ├── actions/                           # Composite actions do GitHub Actions
│   └── workflows/                         # Pipelines declarativos de CI e release
├── app/                                   # Raiz da aplicação Python
│   ├── README.md                          # Visão geral da aplicação
│   ├── src/                               # Código-fonte organizado em camadas DDD/Hexagonal
│   │   ├── README.md                      # Descrição das 4 camadas
│   │   ├── domain/                        # Entidades, Value Objects e Domain Services
│   │   ├── application/                   # Casos de uso e portas abstratas
│   │   ├── infrastructure/                # Adaptadores de rede, persistência e configurações
│   │   └── presentation/                  # Entrypoints executáveis e Composition Root
│   ├── tests/                             # Suíte de testes com branch coverage 100%
│   │   ├── README.md                      # Diretrizes de testes
│   │   ├── unit/                          # Testes unitários rápidos e isolados
│   │   └── integration/                   # Testes de integração de adaptadores
│   │       └── README.md                  # Testes dos gateways de IO
│   ├── scripts/                           # Scripts operacionais e de validação
│   │   ├── README.md                      # Documentação dos scripts
│   │   ├── operations/                    # Runner central de quality gates (clean_workspace.py)
│   │   └── setup.sh                       # Inicializador de ambiente
│   ├── pyproject.toml                     # Configuração de build, pytest, coverage e linters
│   ├── requirements.txt                   # Dependências diretas de runtime
│   └── requirements-dev.txt               # Dependências de desenvolvimento e análise estática
├── docs/                                  # Documentação viva do sistema
│   ├── README.md                          # Índice da documentação técnica
│   ├── arquitetura.md                     # Especificação de arquitetura e políticas de negócio
│   ├── structure.md                       # Estrutura do repositório (este documento)
│   ├── engineering-python.md              # Padrões de engenharia de software em Python
│   ├── engineering-logging.md             # Padrões de observabilidade e logging semântico
│   ├── infra-docker.md                    # Engenharia de contêineres e execução
│   └── devops.md                          # Matriz de CI/CD, estágios e automação
├── infra/                                 # Artefatos de infraestrutura
│   ├── README.md                          # Índice de infraestrutura
│   └── docker/                            # Dockerfile multi-stage, compose e scripts de contêiner
├── linters/                               # Configuração de commitlint e release
│   ├── README.md                          # Governança de commits e git hooks
│   └── releaserc.json                     # Configuração de versionamento semântico
├── logs/                                  # Diretório de logs em tempo real (.gitkeep)
├── Makefile                               # Interface unificada de automação de tarefas
├── AGENTS.md                              # Diretrizes canônicas para agentes inteligentes
├── prompt-model.md                        # Contrato sênior reutilizável para novos projetos
├── README.md                              # Apresentação executiva do repositório
├── .env.example                           # Modelo de configuração de variáveis de ambiente
└── run.py                                 # Ponto de entrada de conveniência para execução local
```

## 2. Invariantes de Dependência e Camadas

1. **Unidirecionalidade das Camadas**:
   - `domain` e `application` nunca realizam imports de `infrastructure` ou `presentation`.
   - `infrastructure` e `presentation` dependem exclusivamente dos contratos definidos em `application` e das entidades de `domain`.
2. **Composition Root**:
   - O módulo `presentation/worker/main.py` atua como o composition root do daemon de monitoramento contínuo: instancia as configurações (`Settings`), inicializa adaptadores concretos e injeta as dependências no caso de uso `CollectAndPublishAlertsUseCase`.
   - O módulo `presentation/cli/ping.py` atua como o composition root do comando de diagnóstico `make app-ping`.
3. **Resolução de Módulos (Imports)**:
   - A raiz do código (`PYTHONPATH`) é fixada em `app/src/`.
   - Todos os imports utilizam caminhos canônicos sem o prefixo redundante `app.src`:
     ```python
     from domain.entities.alert import Alert
     from application.use_cases.poll_monitors import PollMonitorsUseCase
     from infrastructure.config.settings import Settings
     from presentation.worker.main import run
     ```
