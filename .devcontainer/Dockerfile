FROM python:3.11-bookworm

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install System Dependencies (Mirrors setup.yml)
# We include 'qemu-user-static' to ensure internal binary compatibility if needed, though usually handled by host.
RUN apt-get update && apt-get install -y \
    tree \
    git \
    btop \
    rsync \
    fzf \
    ripgrep \
    nano \
    ncdu \
    tmux \
    usbutils \
    pciutils \
    sox \
    ffmpeg \
    stress \
    podman \
    podman-compose \
    curl \
    # Added for development convenience
    sudo \
    lsb-release \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Install 'uv'
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.cargo/bin/uv /usr/local/bin/uv

# 3. Create non-root user 'vscode' (if not already handled by features, but good to be explicit for base compat)
# Note: The common-utils feature in devcontainer.json handles the complex user setup, 
# but we ensure the groups exist.
# The user 'vscode' needs to be in 'audio' group for sound access parity
RUN groupadd -f audio && \
    groupadd -f docker

# 4. Set Workspace Directory
WORKDIR /workspace

# 5. Environment Variables for Parity
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Audio & Device Mocking Env Vars (Optional - can be overridden in .env)
# ENV PULSE_SERVER=unix:/run/user/1000/pulse/native 
