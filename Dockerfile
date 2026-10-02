FROM node:22-slim AS frontend
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.13-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra contree --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --extra contree
COPY cases ./cases
COPY --from=frontend /app/frontend/dist ./frontend/dist
RUN useradd --create-home --uid 1000 borges \
    && mkdir -p /app/runs /app/.borges \
    && chown -R borges:borges /app/runs /app/.borges
USER borges
VOLUME /app/.borges
ENV BORGES_FRONTEND_DIST=/app/frontend/dist \
    BORGES_CASES_DIR=/app/cases \
    BORGES_RUNS_DIR=/app/runs \
    BORGES_HOME=/app/.borges \
    BORGES_REGISTRY_ENFORCE=true
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"
CMD ["borges", "serve", "--host", "0.0.0.0", "--port", "8000"]
