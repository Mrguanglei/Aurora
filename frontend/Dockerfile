# syntax=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/docker/dockerfile:1
# ---- Base Stage ----
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:22-slim AS base

# Install dependencies only when needed
FROM base AS deps

WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* .npmrc* ./

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    make \
    g++ \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,id=yarn-cache,target=/root/.cache/yarn \
    --mount=type=cache,id=npm-cache,target=/root/.npm \
    --mount=type=cache,id=pnpm-store,target=/root/.pnpm-store \
  if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci --cache /root/.npm; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm i --frozen-lockfile --store=/root/.pnpm-store; \
  else echo "Lockfile not found." && exit 1; \
  fi


# ---- Builder Stage ----
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Next.js collects completely anonymous telemetry data about general usage.
# Learn more here: https://nextjs.org/telemetry
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_OUTPUT=standalone
# Skip static page generation during build (prevents prerender errors with client-side auth)
ENV NEXT_SKIP_STATIC_OPTIMIZATION=true

# 接受並使用构建时的编辨伙变量
ARG NEXT_PUBLIC_BACKEND_URL
ARG NEXT_PUBLIC_ENV_MODE=staging
ENV NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL:-http://backend:8011/v1}
ENV NEXT_PUBLIC_ENV_MODE=${NEXT_PUBLIC_ENV_MODE}

RUN \
  if [ -f yarn.lock ]; then SKIP_EXPORT=true yarn run build; \
  elif [ -f package-lock.json ]; then SKIP_EXPORT=true npm run build; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && SKIP_EXPORT=true pnpm run build; \
  else echo "Lockfile not found." && exit 1; \
  fi

# ---- Runner Stage ----
FROM base AS runner
WORKDIR /app

ENV NEXT_PUBLIC_VERCEL_ENV=production
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000

# server.js is created by next build from the standalone output
# https://nextjs.org/docs/pages/api-reference/config/next-config-js/output
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]