# Linters, Git Hooks e Governança de Commits

Especificação dos padrões de qualidade de código, análise estática e automações de hooks locais do repositório **Nagstamon Headless**.

## 1. Pre-commit e Paridade com CI

A configuração de hooks em `.pre-commit-config.yaml` espelha com exatidão a matriz de validação do pipeline de CI (`.github/workflows/ci.yml`), operando sob o princípio de interrupção imediata na primeira falha (`fail_fast: true`):

1. **Commitlint**: Validação da mensagem de commit no hook `commit-msg`.
2. **Área Python**: `Lint` -> `Segurança` -> `Testes` -> `Validate` -> `Build`.
3. **Área Docker**: `Lint` -> `Segurança` -> `Testes` -> `Validate` -> `Build`.
4. **Área GitHub**: `Lint` -> `Segurança` -> `Testes` -> `Validate` -> `Build`.
5. **Área Scripts**: `Lint` -> `Segurança` -> `Testes` -> `Validate` -> `Build`.

## 2. Instalação e Execução de Hooks

```bash
# Instalação dos hooks no repositório git local
make app-pre-commit

# Execução manual dos hooks sobre toda a árvore de arquivos
make app-pre-commit-run
```

## 3. Especificação do Commitlint

A governança de mensagens exige aderência à convenção Conventional Commits (`linters/commitlint.config.mjs`):

- **Tipos Permitidos**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **Idioma**: Português brasileiro.
- **Estrutura**: `<tipo>(<escopo opcional>): <descrição em letras minúsculas>`.
- **Exemplo**: `feat(alert-engine): adiciona suporte a carência dinâmica por tipo de incidente`.

## 4. Análise de Segurança Estática

- **Gitleaks**: Varredura de credenciais corporativas, tokens de API ou certificados acidentalmente versionados. Configurado em `.gitleaks.toml`.
- **Bandit & Safety**: Auditoria de segurança de código Python e inventário de vulnerabilidades conhecidas em dependências de terceiros.
- **Trivy**: Inspeção de vulnerabilidades conhecidas em camadas de imagem Docker e configurações de infraestrutura.
