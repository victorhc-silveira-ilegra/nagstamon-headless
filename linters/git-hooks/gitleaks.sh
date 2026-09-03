#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "[ERRO] gitleaks nao encontrado (mesmo requisito do job CI Python)."
  exit 1
fi

exec gitleaks detect --source . --verbose --redact
