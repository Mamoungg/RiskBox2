#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f apps/web/.env.local ]]; then
  echo "Create apps/web/.env.local from apps/web/.env.example (SANDBOX_API_URL, SANDBOX_SERVER_API_KEY)."
  exit 1
fi

exec pnpm dev:web
