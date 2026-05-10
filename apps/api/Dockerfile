# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml README.md ./
COPY src ./src

RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"

FROM base AS api

EXPOSE 8000

CMD ["uvicorn", "preflight_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
