# Aplicação Nagstamon Headless

Núcleo de código-fonte, suíte de testes e automações do projeto Nagstamon Headless.

## Estrutura do Diretório

- [src/](src/): Código-fonte da aplicação organizado estritamente em conformidade com Domain-Driven Design (DDD) e Arquitetura Hexagonal (`domain`, `application`, `infrastructure`, `presentation`).
- [tests/](tests/): Suíte automatizada de testes com garantia inegociável de 100% de cobertura de branches (`unit` e `integration`).
- [scripts/](scripts/): Utilitários de operação, setup e scripts dos quality gates do repositório.
- `pyproject.toml` / `requirements.txt`: Definição e lock de dependências do ambiente Python.

Para diretrizes de arquitetura e padrões de codificação, consulte [docs/arquitetura.md](../docs/arquitetura.md) e [docs/engineering-python.md](../docs/engineering-python.md).
