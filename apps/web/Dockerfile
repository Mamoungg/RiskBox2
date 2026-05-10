# syntax=docker/dockerfile:1
# Build from repository root: docker build -f apps/web/Dockerfile .
FROM node:22-bookworm-slim AS deps

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/shared-types/package.json ./packages/shared-types/

RUN pnpm install --frozen-lockfile

FROM deps AS builder

COPY apps/web ./apps/web
COPY packages/shared-types ./packages/shared-types

ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm --filter web build

FROM node:22-bookworm-slim AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME=0.0.0.0

CMD ["node", "apps/web/server.js"]
