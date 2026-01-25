FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install system dependencies
# libjemalloc2 is required to fix "Unsupported system page size" errors on RPi (64k pages)
# by forcing usage of system allocator instead of polars' bundled jemalloc.
RUN apt-get update && apt-get install -y \
    curl \
    libjemalloc2 \
    && rm -rf /var/lib/apt/lists/*

# Preload system jemalloc
ENV LD_PRELOAD=libjemalloc.so.2

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/

CMD ["python", "src/main.py"]
