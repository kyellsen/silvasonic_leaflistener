
# --- Stage 1: Builder ---
FROM python:3.11-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libpq-dev \
    libsndfile1-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create venv and install dependencies
# Install dependencies
COPY pyproject.toml uv.lock ./
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN git config --global http.postBuffer 524288000 && \
    git config --global http.lowSpeedLimit 0 && \
    git config --global http.lowSpeedTime 999999 && \
    uv venv && \
    uv lock && \
    uv export --frozen --no-emit-project --no-dev --format requirements-txt > requirements.txt && \
    uv pip install --no-cache -r requirements.txt


# --- Stage 2: Runtime ---
FROM python:3.11-slim-bookworm

# Install runtime dependencies
# libsndfile1 for audio, ffmpeg for resizing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY src/ src/

# Copy default config
RUN mkdir -p /etc/birdnet
COPY config.yml /etc/birdnet/config.yml

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Command to run
CMD ["python", "-m", "silvasonic_birdnet.main"]

