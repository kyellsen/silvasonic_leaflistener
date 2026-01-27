FROM python:3.11-slim-bookworm

# Install system dependencies
# - rclone: The core sync engine
# - curl: Useful for healthchecks
RUN apt-get update && apt-get install -y \
    rclone \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install python dependencies from pyproject.toml
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src /app/src

# Set PYTHONPATH
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python3", "-m", "silvasonic_uploader.main"]
