FROM python:3.11-slim-bookworm

# Install system dependencies
# libsndfile1: for librosa/soundfile reading
# ffmpeg: for extensive audio format support
# curl: for installing uv
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create user pi
RUN groupadd -g 1000 pi && \
    useradd -m -u 1000 -g pi -s /bin/bash pi

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .

# Install dependencies (system-wide in the container, but isolated)
RUN uv pip install --system -r pyproject.toml

# Copy source code
COPY src/ ./src/

# Set permissions
RUN chown -R pi:pi /app

# Switch to user pi
USER pi

# Environment variables
# Set PYTHONPATH
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "silvasonic_processor.main"]
