FROM python:3.11-slim-bookworm

WORKDIR /app

# No external dependencies currently needed beyond standard lib for this simple version
# If future needs arise, COPY requirements.txt . && pip install -r requirements.txt

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ /app/src/

# Create silvasonic group/user for rootless consistency if needed, 
# but usually we run as effective user from Podman.
# We just need to make sure we can read/write to the mounted volumes.
# The host user UID 1000 usually maps to 0 inside rootless container unless --userns=keep-id.
# Assuming standard Silvasonic podman setup.

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

CMD ["python", "src/main.py"]
