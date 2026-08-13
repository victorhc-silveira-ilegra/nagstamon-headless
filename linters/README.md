# GitHooks e linters — Nagstamon Headless

## Pre-commit (Python)

Requer repositorio git. Depois:

```bash
make app-pre-commit
```

Ou:

```bash
bash linters/git-hooks/install.sh
```

## Commitlint (Node.js, fora do pip)

Requer Node.js + npm. O hook `commit-msg` usa:

```bash
npx --yes -p @commitlint/cli -p @commitlint/config-conventional \
  commitlint --config linters/commitlint.config.mjs --edit
```

Config: [`commitlint.config.mjs`](commitlint.config.mjs)

## CI seguranca (binario, fora do pip)

- **gitleaks** — varredura de secrets (quando houver CI)
- Config do repositorio: [`.gitleaks.toml`](../.gitleaks.toml)
