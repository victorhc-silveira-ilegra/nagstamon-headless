# GitHooks e linters — Nagstamon Headless

## Pre-commit (= matriz CI)

`fail_fast: true`. Mesmas areas e stages do [`.github/workflows/ci.yml`](../.github/workflows/ci.yml):

1. Commitlint (local; tambem no stage `commit-msg`)
2. Python: Lint → Seguranca → Gitleaks → Testes → Validate → Build
3. Docker: Lint → Seguranca → Testes → Validate → Build
4. GitHub: Lint → Seguranca → Testes → Validate → Build
5. Scripts: Lint → Seguranca → Testes → Validate → Build

Ferramentas extras (como no CI): `npx` (commitlint), `gitleaks`, `hadolint`, `trivy`, `actionlint`, `docker`.

```bash
make app-pre-commit
```

Ou:

```bash
bash linters/git-hooks/install.sh
```

## Commitlint (Node.js, fora do pip)

Requer Node.js + npm. Script: [`git-hooks/commitlint.sh`](git-hooks/commitlint.sh)

```bash
bash linters/git-hooks/commitlint.sh .git/COMMIT_EDITMSG
```

Config: [`commitlint.config.mjs`](commitlint.config.mjs)

## CI seguranca (binario, fora do pip)

- **gitleaks** — job Python e area GitHub; hook local [`git-hooks/gitleaks.sh`](git-hooks/gitleaks.sh)
- Config: [`.gitleaks.toml`](../.gitleaks.toml)

## Release

semantic-release (`linters/releaserc.json`) no job `release` apos a matriz CI em `main`. Template: [`.github/workflows/templates/release-announcement.yaml`](../.github/workflows/templates/release-announcement.yaml).
