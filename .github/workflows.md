# GitHub Actions

Pipelines de integracao e release do Nagstamon Headless.

Documentacao: [docs/devops.md](../docs/devops.md).

## Composite actions

```text
.github/actions/
├── shared/
│   └── pipeline-summary/
└── ci/
    ├── setup-python/
    ├── validate-docker/
    ├── validate-github/
    ├── validate-scripts/
    ├── release/
    └── sync-tags/
```

## Workflows

| Workflow | Gatilho | Uso |
|----------|---------|-----|
| [ci.yml](workflows/ci.yml) | push/PR `main`, manual | CI matriz; release no push `main` |
