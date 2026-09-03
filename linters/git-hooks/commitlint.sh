#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

MSG_FILE="${1:-}"
if [[ -z "${MSG_FILE}" ]]; then
  if [[ ! -f "${REPO_ROOT}/.git/index.lock" ]]; then
    echo "[OK] Commitlint: sem commit em andamento; pulando no pre-commit run"
    exit 0
  fi
  MSG_FILE="${REPO_ROOT}/.git/COMMIT_EDITMSG"
fi

if [[ ! -f "${MSG_FILE}" ]]; then
  echo "[ERRO] Commitlint: arquivo de mensagem ausente: ${MSG_FILE}"
  exit 1
fi

if ! grep -Eqv '^[[:space:]]*(#|$)' "${MSG_FILE}"; then
  echo "[OK] Commitlint: mensagem vazia ou so comentarios; validacao no stage commit-msg"
  exit 0
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "[ERRO] npx nao encontrado. Instale Node.js/npm para o commitlint."
  exit 1
fi

exec npx --yes -p @commitlint/cli -p @commitlint/config-conventional \
  commitlint --config linters/commitlint.config.mjs --edit "${MSG_FILE}"
