# ── Python backend base ──────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

WORKDIR /app

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev, no cache for small image)
RUN uv sync --frozen --no-cache --no-dev

# Copy application code
COPY eden/ ./eden/
COPY data/ ./data/

ENV PYTHONUNBUFFERED=1

# ── Dashboard API (default) ──────────────────────────────────────────
FROM base AS api
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')" || exit 1
CMD ["uv", "run", "python", "-m", "eden"]

# ── AgentCore Runtime ────────────────────────────────────────────────
FROM base AS runtime
EXPOSE 8080
CMD ["uv", "run", "python", "-m", "eden.runtime_entry"]

# ── Dashboard frontend (build + nginx serve) ─────────────────────────
FROM public.ecr.aws/docker/library/node:22-alpine AS dashboard-build
WORKDIR /app
COPY eden-dashboard/package.json eden-dashboard/package-lock.json* ./
RUN npm ci --ignore-scripts 2>/dev/null || npm install
COPY eden-dashboard/ ./
RUN npm run build

FROM public.ecr.aws/docker/library/nginx:alpine AS dashboard
COPY --from=dashboard-build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD wget -qO- http://localhost:3000/ || exit 1
