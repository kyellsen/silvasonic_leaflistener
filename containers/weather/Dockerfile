FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install system dependencies
# libpq-dev is needed for psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY pyproject.toml .

# Install dependencies (use pre-built wheels for polars)
RUN pip install --no-cache-dir .

COPY src/ src/

CMD ["python", "src/main.py"]
