FROM python:3.13-slim

# Install system dependencies
# - rclone: The core sync engine
# - curl: Useful for healthchecks
RUN apt-get update && apt-get install -y \
    rclone \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install python dependencies from pyproject.toml
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src /app/src

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Default command
CMD ["python3", "-u", "src/main.py"]
