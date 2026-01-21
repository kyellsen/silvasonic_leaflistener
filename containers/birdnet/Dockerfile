FROM python:3.11-slim

# Install system dependencies
# libsndfile1 for audio loading, ffmpeg for resizing/resampling
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python dependencies
COPY pyproject.toml .
# We install numpy first to avoid build isolation issues with some audio libs if they occur
RUN uv pip install --system --no-cache numpy
RUN uv pip install --system --no-cache .

# Copy source code
COPY src/ src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Command to run
CMD ["python", "src/main.py"]
