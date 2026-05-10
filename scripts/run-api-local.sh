#!/usr/bin/env bash
# Run the FastAPI app locally (no Docker). Requires Python 3.12+, Postgres, Redis.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
INFRA_ENV="$ROOT/infra/.env"

pick_python() {
  for cmd in python3.12 python3.13 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
      if "$cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

if [[ -f "$INFRA_ENV" ]]; then
  echo "Loading environment from infra/.env"
  set -a
  # shellcheck disable=SC1090
  source "$INFRA_ENV"
  set +a
else
  echo "Warning: infra/.env not found. Copy infra/.env.example to infra/.env and edit."
fi

PY="$(pick_python)" || {
  echo ""
  echo "This project needs Python 3.12 or newer. Your default python3 may be 3.9 (macOS)."
  echo "Install with Homebrew, then retry:"
  echo "  brew install python@3.12"
  echo '  echo '\''export PATH="/opt/homebrew/opt/python@3.12/bin:$PATH"'\'' >> ~/.zshrc && source ~/.zshrc'
  echo ""
  exit 1
}

echo "Using interpreter: $PY ($($PY --version))"

cd "$API_DIR"
if [[ ! -d .venv ]]; then
  echo "Creating virtualenv at apps/api/.venv"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip setuptools wheel >/dev/null
python -m pip install -e . >/dev/null

echo "Starting API on http://127.0.0.1:8000 (docs: /docs)"
exec uvicorn preflight_api.main:app --reload --host 0.0.0.0 --port 8000
