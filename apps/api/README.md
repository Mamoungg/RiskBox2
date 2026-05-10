# preflight-api

FastAPI service for Agent Preflight Sandbox. Install with [uv](https://github.com/astral-sh/uv):

```bash
uv sync
uv run uvicorn preflight_api.main:app --reload --host 0.0.0.0 --port 8000
```

Run the Temporal worker:

```bash
uv run python -m preflight_api.temporal.worker
```
