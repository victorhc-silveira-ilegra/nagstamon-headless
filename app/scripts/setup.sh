#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r app/requirements.txt -r app/requirements-dev.txt
python -m pip install -e app

if [[ -d .git ]]; then
  bash linters/git-hooks/install.sh
else
  echo "[AVISO] Sem repositorio git; hooks nao instalados."
fi

echo "[OK] Ambiente Linux configurado (.venv)."
