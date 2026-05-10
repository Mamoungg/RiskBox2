# Agent Preflight Sandbox

Machine-to-machine **decision sandbox** for AI agents: evaluate a proposed risky action before execution by combining repository and policy grounding (Nia), codebase risk signals (Greptile), payment and settlement simulation (AllScale), and an LLM verdict via LiteLLM.

## Architecture

- **apps/api** — FastAPI service: API key auth, `POST /api/v1/sandbox/evaluate`, Redis cache and rate limits, Postgres persistence, Temporal-orchestrated evaluation.
- **apps/web** — Next.js 15 demo dashboard (optional inspection UI; proxies to the API with a server-side key).
- **packages/shared-types** — Shared TypeScript types aligned with the evaluate contract.
- **infra** — `docker-compose.yml` and `.env.example` for local production-style stacks.

## Quick start (Docker)

```bash
cd infra
cp .env.example .env
# Edit .env: set SANDBOX_API_KEYS, optional LLM and vendor keys
docker compose up --build
```

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Web demo: `http://localhost:3000`
- Temporal UI: `http://localhost:8080`

The Compose file starts both the **API** and the **Temporal worker**. Evaluations are orchestrated on Temporal whenever `TEMPORAL_TARGET` is set (as in Compose). If the worker is unhealthy, `/evaluate` calls can hang until they time out.

Call the evaluate endpoint:

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

## Local development (without Docker for Node)

### Backend (uv)

```bash
cd apps/api
uv sync
uv run uvicorn preflight_api.main:app --reload --host 0.0.0.0 --port 8000
```

Run the Temporal worker in another terminal:

```bash
cd apps/api
uv run python -m preflight_api.temporal.worker
```

### Frontend (pnpm)

```bash
pnpm install
pnpm dev:web
```

Point `apps/web/.env.local` at `SANDBOX_API_URL` and `SANDBOX_SERVER_API_KEY` (see `apps/web/.env.example`).

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
