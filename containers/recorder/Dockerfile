FROM python:3.13-slim-bookworm

# Install system dependencies for audio
# alsa-utils for arecord, ffmpeg for FLAC encoding
RUN apt-get update && apt-get install -y \
    libasound2 \
    alsa-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies using uv.lock
# 1. Copy dependency definitions
COPY pyproject.toml uv.lock ./

# 2. Install dependencies (system-wide, no cache)
RUN uv lock && \
    uv export --frozen --no-dev --format requirements-txt > requirements.txt && \
    uv pip install --system --no-cache -r requirements.txt

# 3. Copy source code
COPY src/ /app/src/

# Create recording directory
RUN mkdir -p /data/recording

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV AUDIO_OUTPUT_DIR=/data/recording
# Add src to PYTHONPATH so we can run as a module
ENV PYTHONPATH=/app/src

# Run as module
CMD ["python", "-m", "main"]
