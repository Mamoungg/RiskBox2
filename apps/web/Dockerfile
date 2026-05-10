FROM node:20-alpine

WORKDIR /repo
ENV NEXT_TELEMETRY_DISABLED=1

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/shared-types/package.json ./packages/shared-types/

RUN pnpm install

COPY apps/web ./apps/web
COPY packages/shared-types ./packages/shared-types

RUN pnpm --filter web build

EXPOSE 3000

WORKDIR /repo
CMD ["pnpm", "--filter", "web", "exec", "next", "start", "-H", "0.0.0.0", "-p", "3000"]
