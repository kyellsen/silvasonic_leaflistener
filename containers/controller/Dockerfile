# --- Stage 1: Builder ---
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libasound2-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy pyproject.toml and README.md
COPY pyproject.toml README.md ./

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Create venv and install dependencies
RUN uv venv && \
    uv pip install --no-cache -r pyproject.toml

# Copy source code and install package
COPY src ./src
RUN uv pip install --no-cache .


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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY src /app/src

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Create default directories
RUN mkdir -p /app/mic_profiles

CMD ["python", "-m", "silvasonic_controller.main"]

