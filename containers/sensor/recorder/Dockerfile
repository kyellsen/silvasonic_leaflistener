
FROM python:3.13-slim

# Install system dependencies for audio
# libasound2-dev and libportaudio2 are crucial for sounddevice
RUN apt-get update && apt-get install -y \
    libasound2 \
    libasound2-dev \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create recording directory (just in case volume not mounted, though it should be)
RUN mkdir -p /data/recording

# Set environment variables with defaults
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
