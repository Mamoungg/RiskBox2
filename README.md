# Agent Preflight Sandbox

Machine-to-machine **decision sandbox** for AI agents: evaluate a proposed risky action before execution by combining repository and policy grounding (Nia), codebase risk signals (Greptile), payment and settlement simulation (AllScale), and an LLM verdict via LiteLLM.

## Architecture

- **apps/api** — FastAPI service: API key auth, `POST /api/v1/sandbox/evaluate`, Redis cache and rate limits, Postgres persistence, optional Temporal-orchestrated evaluation.
- **apps/web** — Next.js 15 demo dashboard (optional inspection UI; proxies to the API with a server-side key).
- **packages/shared-types** — Shared TypeScript types aligned with the evaluate contract.
- **infra** — `.env.example` template for local configuration and `docker-compose.yml` for a full Docker stack.

## Prerequisites

For **local development without Docker**, install yourself (Homebrew, cloud, or another path):

- **PostgreSQL** (for `DATABASE_URL`)
- **Redis** (for `REDIS_URL`)
- **Optional:** a **Temporal** dev server on `localhost:7233` if you set `TEMPORAL_TARGET`; otherwise leave `TEMPORAL_TARGET` unset and evaluations run **inline** in the API (no worker process needed).

## Quick start (Docker)

From the repository root:

```bash
cd infra
cp .env.example .env
# Edit .env: set SANDBOX_API_KEYS (and optional LLM / vendor keys). Use SANDBOX_SERVER_API_KEY equal to one of those keys for the web proxy.
docker compose up --build
```

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Web demo: `http://localhost:3000`
- Temporal UI: `http://localhost:8080`

Compose wires Postgres, Redis, Temporal, the API, a Temporal **worker**, and the Next.js **web** app. `DATABASE_URL`, `REDIS_URL`, and `TEMPORAL_TARGET` for the API and worker are set inside `docker-compose.yml` so services use in-cluster hostnames. If the worker is unhealthy, `/evaluate` calls that use Temporal may hang until they time out.

## Quick start (local, no Docker)

### 1. Configure environment

```bash
cd infra
cp .env.example .env
```

Edit `.env` with your Postgres/Redis URLs, `SANDBOX_API_KEYS`, optional `OPENAI_API_KEY`, and vendor keys as needed. For the web demo, set `SANDBOX_SERVER_API_KEY` to match one of the keys in `SANDBOX_API_KEYS`.

Load the same variables when running the API (e.g. `export $(grep -v '^#' .env | xargs)` from `infra/`, or point your shell at a copy of `.env` in `apps/api/`).

### 2. Backend (Python 3.12 + uv recommended)

```bash
cd apps/api
uv sync
uv run uvicorn preflight_api.main:app --reload --host 0.0.0.0 --port 8000
```

If you use **Temporal**, run the worker in a second terminal:

```bash
cd apps/api
uv run python -m preflight_api.temporal.worker
```

If `TEMPORAL_TARGET` is **unset**, skip the worker; the API runs the full pipeline in-process.

### 3. Frontend (pnpm)

```bash
# from repository root
pnpm install
pnpm dev:web
```

Create `apps/web/.env.local` from `apps/web/.env.example` (`SANDBOX_API_URL`, `SANDBOX_SERVER_API_KEY`).

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Web demo: `http://localhost:3000`

### 4. Call the API

```bash
curl -sS -X POST http://localhost:8000/api/v1/sandbox/evaluate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-local-key" \
  -d '{
    "task_type": "code_and_payment",
    "action_summary": "Merge contractor PR and release payment",
    "repository_url": "https://github.com/vercel/ai",
    "repository_ref": "main",
    "diff_text": "--- a/auth.py\n+++ b/auth.py\n@@\n- return verify(token)\n+ return True",
    "payment_request": {
      "amount": 2500,
      "currency": "USD",
      "recipient": "contractor@example.com",
      "invoice_reference": "INV-123"
    },
    "constraints": { "max_risk_score": 40, "require_citations": true }
  }' | jq
```

Use an `X-API-Key` value that appears in `SANDBOX_API_KEYS`.

## Environment variables

See `infra/.env.example` for the full matrix. Highlights:

| Variable | Purpose |
| --- | --- |
| `SANDBOX_API_KEYS` | Comma-separated plaintext keys (dev); also supports DB-backed keys |
| `DATABASE_URL` | Async Postgres URL for the API (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis for cache + rate limits |
| `TEMPORAL_TARGET` | e.g. `localhost:7233`; if unset, evaluation runs inline |
| `LITELLM_MODEL` | Model string for LiteLLM (e.g. `gpt-4o-mini`) |
| `NIA_API_KEY` / `NIA_BASE_URL` | Nia REST integration |
| `GREPTILE_API_KEY` / `GITHUB_TOKEN` / `GREPTILE_BASE_URL` | Greptile |
| `ALLSCALE_API_KEY` / `ALLSCALE_BASE_URL` | AllScale payment simulation |

If vendor keys are missing, the service returns **structured mock findings** so the stack stays demoable in a hackathon environment.

## Product contract

Verdicts: `SAFE`, `NEEDS_APPROVAL`, `BLOCKED` with `risk_score` 0–100, reasons, safer alternative, per-sponsor assessments, timings, and `run_id` for traceability.

## License

Hackathon MVP — use at your own risk.
