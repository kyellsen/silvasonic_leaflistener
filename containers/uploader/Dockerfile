
# --- Stage 1: Builder ---
FROM python:3.11-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
COPY pyproject.toml uv.lock ./
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN uv venv && \
    uv lock && \
    uv export --frozen --no-emit-project --no-dev --format requirements-txt > requirements.txt && \
    uv pip install --no-cache -r requirements.txt


# --- Stage 2: Runtime ---
FROM python:3.11-slim-bookworm

# Install runtime dependencies
# rclone: The core sync engine
# curl: Useful for healthchecks
# libpq5: Required for psycopg (runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    rclone \
    curl \
    rclone \
    curl \
    rclone \
    curl \
    libpq5 \
    ffmpeg \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY src /app/src

# Set PYTHONPATH
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python3", "-m", "silvasonic_uploader.main"]
