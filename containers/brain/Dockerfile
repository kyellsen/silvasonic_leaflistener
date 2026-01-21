FROM python:3.11-slim-bookworm

# System dependencies for audio analysis (libsndfile for librosa/soundfile)
# and basic tools
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python dependencies
# Install Python dependencies
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# Copy source code
COPY src/ /app/src/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Run the application
CMD ["python", "-m", "src.main"]
