
# --- Stage 1: Builder ---
FROM python:3.11-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
COPY pyproject.toml ./
# Note: uv.lock is missing in repo, so we generate it here
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN uv venv && \
    uv lock && \
    uv export --frozen --no-emit-project --no-dev --format requirements-txt > requirements.txt && \
    uv pip install --no-cache -r requirements.txt


# --- Stage 2: Runtime ---
FROM python:3.11-slim-bookworm

# No external dependencies currently needed beyond standard lib
# If future needs arise, apt-get install here

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY src/ /app/src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "silvasonic_monitor.main"]
