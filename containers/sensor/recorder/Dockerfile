FROM python:3.13-slim

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

# Copy pyproject.toml and install
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# Copy microphone profiles
COPY microphones/ ./microphones/

# Copy application code
COPY mic_profiles.py .
COPY main.py .

# Create recording directory
RUN mkdir -p /data/recording

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV AUDIO_OUTPUT_DIR=/data/recording

CMD ["python", "main.py"]
