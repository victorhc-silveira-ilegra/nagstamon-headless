# Harness de Agentes Inteligentes

Harness universal de engenharia para orientar modelos de linguagem (LLMs), agentes autônomos e assistentes inteligentes em tarefas no Nagstamon Headless.

---

## 1. Princípios de Design do Harness

1. **Agnóstico a Plataforma**: Formato 100% Markdown padronizado com frontmatter YAML padrão, sem dependência de IDEs, plugins ou extensões proprietárias (`.mdc`, etc.).
2. **Arquitetura Sênior Inegociável**: Respeito estrito aos padrões Domain-Driven Design (DDD), Arquitetura Hexagonal (Ports & Adapters) e Test-Driven Development (TDD).
3. **Determinismo Operacional**: Todas as decisões de filtragem, formatação e deduplicação de alertas possuem regras matemáticas e contratuais bem definidas.
4. **Zero Código Morto ou Ruído**: Código autodescritivo sem comentários, tipagem estrita com Python 3.11+ (`mypy strict`), limites de 300 linhas por arquivo e cobertura total de testes (100% de branch coverage).

---

## 2. Estrutura do Diretório

```text
.agents/
├── README.md                                 # Manifesto e governança do harness
├── rules/                                    # Regras arquiteturais e invariantes
│   ├── architecture-hexagonal-ddd.md         # Isolamento de camadas e regras de dependência
│   ├── alert-engine-sla-policy.md            # Motor de filtragem, carências de SLA e janelas
│   ├── observability-semantic-logging.md     # Logging estruturado, eventos e separação de sinks
│   └── code-quality-testing.md               # Padrões TDD, cobertura 100% e quality gates
└── skills/                                   # Habilidades operacionais especializadas
    ├── nagstamon-alert-view/SKILL.md         # Renderização de alertas (stdout e Google Chat)
    ├── nagstamon-alert-engine/SKILL.md       # Deduplicação, persistência e lifecycle do polling
    ├── nagstamon-quality-gate/SKILL.md       # Execução e correção da matriz de 5 estágios
    └── nagstamon-ops/SKILL.md                # Operação do daemon, probes HTTP e testes de fumaça
```

---

## 3. Como os Agentes Devem Consumir este Harness

- **Ponto de Entrada Mestre**: O arquivo [`AGENTS.md`](../AGENTS.md) na raiz do repositório é o contrato principal carregado automaticamente no início de qualquer sessão.
- **Regras Gerais (`rules/`)**: Devem ser aplicadas de forma contínua durante qualquer ciclo de leitura, refatoração, implementação ou depuração.
- **Habilidades (`skills/`)**: Devem ser consultadas sob demanda quando o agente estiver atuando especificamente na área descrita pelo `description` do frontmatter YAML da skill correspondente.
