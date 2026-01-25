FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install system dependencies for building polars from source
# (Required because pre-built wheels are crashing with page size errors)
# We need Rust to build polars.
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (needed for polars build)
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Copy project
COPY pyproject.toml .

# Install dependencies with forced source build for polars
# This ensures jemalloc is compiled against the actual system page size (or disabled if configured)
RUN pip install --no-cache-dir --no-binary=polars .

COPY src/ src/

CMD ["python", "src/main.py"]
