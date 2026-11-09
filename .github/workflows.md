# Workflows de Integração Contínua e Release (GitHub Actions)

Especificação técnica dos workflows de automação, composite actions e gatilhos de execução configurados no GitHub Actions para o repositório **Nagstamon Headless**.

## 1. Mapeamento de Workflows

| Arquivo de Workflow | Gatilhos de Disparo | Responsabilidade Principal |
| :--- | :--- | :--- |
| [ci.yml](workflows/ci.yml) | Push em `main`, Pull Requests para `main`, `workflow_dispatch` | Execução paralela da matriz de qualidade por área e entrega contínua (Semantic Release) |

## 2. Catálogo de Composite Actions Reutilizáveis

As automações de CI/CD utilizam ações compostas modulares localizadas em `.github/actions/`:

```text
.github/actions/
├── shared/
│   └── pipeline-summary/          # Consolidação e publicação de resumo no GitHub Step Summary
└── ci/
    ├── setup-python/              # Configuração do interpretador Python e restauração de caches
    ├── validate-commitlint/       # Validação de mensagens de commit (Conventional Commits)
    ├── validate-python/           # Execução dos quality gates de Python (Lint, Sec, Test, Val, Build)
    ├── validate-docker/           # Execução dos quality gates de Docker (Hadolint, Trivy, build)
    ├── validate-github/           # Validação estrutural de workflows, actions e actionlint
    ├── validate-scripts/          # Análise de scripts shell, permissões e syntax checks
    ├── release/                   # Execução do semantic-release e publicação de artefatos
    └── sync-tags/                 # Sincronização de tags flutuantes de versão maior (ex.: v1)
```

## 3. Comportamento Operacional e Filtros

- **Push na Branch `main`**: Dispara a execução paralela de todas as áreas (`python`, `docker`, `github`, `scripts`). Quando todas as etapas concluem com sucesso, aciona o job de `release`, exceto se houver indicação de `[skip-cd]` na mensagem de commit.
- **Pull Requests**: Dispara a validação de todas as 4 áreas para assegurar que nenhum código seja integrado sem 100% de conformidade com os quality gates.
- **Disparo Manual (`workflow_dispatch`)**: Permite acionamento sob demanda via interface web do GitHub ou CLI `gh`, suportando o parâmetro booleano `skip_cd` para controlar a publicação de releases.

Para detalhes completos sobre a esteira de entrega, consulte [docs/devops.md](../docs/devops.md).
