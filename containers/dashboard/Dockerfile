FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (if any needed for psutil or others)
# psutil often needs gcc if no wheel is available, but usually wheels exist.
# curl is useful for healthchecks.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    build-essential \
    pkg-config \
    libpq-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Download frontend dependencies (Plotly)
RUN mkdir -p /app/src/static/js && \
    curl -L -o /app/src/static/js/plotly.min.js https://cdn.plot.ly/plotly-2.27.0.min.js

# Install python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY src /app/src

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
