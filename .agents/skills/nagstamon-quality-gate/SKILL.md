---
name: nagstamon-quality-gate
description: Protocolo de execução, diagnóstico e conformidade dos quality gates unificados do repositório
---

# Skill: Nagstamon Quality Gate

Esta habilidade rege a execução e conformidade do orquestrador de qualidade `clean_workspace.py` e suas interfaces Makefile.

## Matriz de Validação

O ecossistema de validação é estruturado em 4 áreas temáticas e 5 estágios determinísticos:

| Área | Estágios Cobertos | Responsabilidade |
| :--- | :--- | :--- |
| `python` | `lint`, `security`, `test` | Ruff, Flake8, Bandit, Safety, Pytest (100% branch coverage) |
| `docker` | `lint`, `security`, `validate`, `build` | Hadolint, Trivy, Dockerfile lint, Build smoke |
| `github` | `validate` | Ações locais, integridade estrutural de workflows CI |
| `scripts`| `lint`, `security` | ShellCheck, permissões e análise de scripts operacionais |

## Comandos Principais

Execução via atalhos do `Makefile`:

```bash
# Validações estáticas e linter
make app-lint

# Análise estática de segurança e vulnerabilidades de dependências
make app-security

# Execução da suíte completa de testes com branch coverage 100%
make app-test

# Validação completa de todas as áreas (equivalente ao pipeline de CI)
make clean-workspace
```

Execução direcionada via runner CLI:

```bash
# Executa apenas área Python
python clean_workspace.py --area python

# Executa estágio específico em uma área
python clean_workspace.py --area python --stage test
```

## Diretrizes de Resolução de Falhas

1. **Falha de Cobertura (`pytest-cov`)**:
   - Nenhuma linha ou desvio condicional (`branch`) pode ficar sem cobertura nos testes unitários e de integração (`app/tests/`).
   - Não use pragmas `# pragma: no cover` para contornar código não testado, exceto quando formalmente justificado em blocos puramente defensivos de runtime do SO.
2. **Falha de Segurança (`bandit`)**:
   - Não suprimir avisos com `# nosec`. Corrija a causa raiz (ex.: uso de `contextlib.suppress` em vez de blocos de exceção vazios, binds explícitos em interfaces seguras, sanitização de caminhos).
3. **Ausência de Comentários**:
   - O código-fonte em Python não deve conter comentários nem docstrings não canônicas. O código expressa suas intenções por meio de tipagem estrita e nomes semânticos.
