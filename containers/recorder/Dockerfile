
# --- Stage 1: Builder ---
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
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

# Install system dependencies for audio
# alsa-utils for arecord, ffmpeg for FLAC encoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2 \
    alsa-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY src/ /app/src/

# Create recording directory
RUN mkdir -p /data/recording

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV AUDIO_OUTPUT_DIR=/data/recording
ENV PYTHONPATH=/app/src

# Run as module
CMD ["python", "-m", "main"]

