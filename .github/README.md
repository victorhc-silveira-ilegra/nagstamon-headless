# Governança e Automações GitHub (.github)

Diretório dedicado à configuração de pipelines de Integração Contínua (CI), automações de entrega e governança do repositório no GitHub.

## Estrutura

- [workflows/](workflows/): Workflows de GitHub Actions para execução de testes, quality gates e releases semânticas.
- [actions/](actions/): Composite actions modulares reutilizadas nos workflows de CI (`setup-python`, `validate-github`, `validate-docker`, `validate-scripts`, etc.).
- [workflows.md](workflows.md): Especificação detalhada dos jobs de CI/CD e matriz de validação.

Para especificações detalhadas sobre a esteira de entrega e releases, consulte [docs/devops.md](../docs/devops.md).
