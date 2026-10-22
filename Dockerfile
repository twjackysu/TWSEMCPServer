# syntax=docker/dockerfile:1

# Both stages use the same image, so the virtualenv built in the first finds its interpreter in the second.
ARG PYTHON_IMAGE=python:3.13-slim

# ---- Build: the locked runtime dependencies (uv.lock, no dev extras) into /app/.venv ----
FROM ${PYTHON_IMAGE} AS builder
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- Runtime: the virtualenv and the source only (no uv, no build tools), as a non-root user ----
FROM ${PYTHON_IMAGE}
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
# One COPY per package (tests/unit/test_layering_unit.py checks every package is listed). Owned by
# root and only readable by the app user, which runs the server.
COPY server.py ./
COPY tools/ ./tools/
COPY toolkit/ ./toolkit/
COPY services/ ./services/
COPY sources/ ./sources/
COPY utils/ ./utils/
COPY prompts/ ./prompts/
USER app

# HTTP transport (default): PORT, 8000 unless set. `docker run -i -e MCP_STDIO=1` serves stdio instead.
EXPOSE 8000
# Under HTTP, GET /health (no upstream call); under stdio there is no port to probe, so it reports healthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, sys, urllib.request; os.environ.get('MCP_STDIO', '').lower() in ('1', 'true') and sys.exit(0); urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '8000'), timeout=4)"

CMD ["python", "server.py"]
