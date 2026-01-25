FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    sox \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python dependencies using the main project's pyproject.toml
# Assumes build context is the project root (silvasonic)
COPY containers/birdnet/pyproject.toml .

# Install numpy first for build isolation
RUN uv pip install --system --no-cache numpy

# Install dependencies
RUN uv pip compile pyproject.toml -o requirements.txt && \
    uv pip install --system --no-cache -r requirements.txt

# Copy source code


# Copy test runner
COPY containers/birdnet_test/test_runner.py /app/test_runner.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LOCATION_FILTER_ENABLED=false
ENV MIN_CONFIDENCE=0.01
# Ensure the analyzer doesn't try to use the DB
ENV DB_PATH=/tmp/mock.sqlite

# Create results directory
RUN mkdir -p /data/db/results

CMD ["python", "test_runner.py"]
