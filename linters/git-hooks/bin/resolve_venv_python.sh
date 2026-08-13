#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CFG="${REPO_ROOT}/config/python.json"
VENV_NAME=".venv"

if [[ -f "${CFG}" ]]; then
  PARSED="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('venv_path','.venv'))" "${CFG}" 2>/dev/null || true)"
  if [[ -n "${PARSED}" ]]; then
    VENV_NAME="${PARSED}"
  fi
fi

CANDIDATES=(
  "${REPO_ROOT}/${VENV_NAME}/bin/python"
  "${REPO_ROOT}/.venv/bin/python"
)

for candidate in "${CANDIDATES[@]}"; do
  if [[ -x "${candidate}" ]]; then
    echo "${candidate}"
    exit 0
  fi
done

command -v python3
