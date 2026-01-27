# --- Stage 1: Builder ---
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy pyproject.toml
COPY pyproject.toml ./

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Create venv and install dependencies directly from pyproject.toml
# We use --no-cache to avoid saving cache in the image
RUN uv venv && \
    uv pip install --no-cache -r pyproject.toml


# --- Stage 2: Runtime ---
FROM python:3.11-slim-bookworm

# Install system dependencies
# - podman: For CLI orchestration
# - alsa-utils: For 'arecord -l' device discovery
# - udev: For device events
RUN apt-get update && apt-get install -y --no-install-recommends \
    podman \
    alsa-utils \
    udev \
    libasound2-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY src /app/src


ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "-m", "src.main"]
