FROM python:3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    tree git btop rsync fzf ripgrep nano ncdu tmux \
    usbutils pciutils sox ffmpeg stress \
    podman podman-compose curl sudo lsb-release \
    # Playwright Dependencies
    libwoff1 libopus0 libwebp7 libwebpdemux2 libenchant-2-2 \
    libsecret-1-0 libhyphen0 libgdk-pixbuf2.0-0 libegl1 \
    libnotify4 libxslt1.1 libevent-2.1-7 libgles2 libvpx7 \
    libxcomposite1 libatk1.0-0 libatk-bridge2.0-0 libepoxy0 \
    libgtk-3-0 libharfbuzz-icu0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Install 'uv'
ENV UV_INSTALL_DIR="/usr/local/bin"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Fix GID Collision
# Wir schieben die Gruppe 'podman' (oder docker) auf 999,
# damit das Feature 'common-utils' die ID 1000 für 'vscode' nutzen kann.
RUN groupadd -f audio && \
    groupadd -g 999 -f podman

# 4. Set Workspace Directory (Konsistent mit devcontainer.json)
# Bereite den Ordner vor, damit Rechte stimmen
RUN mkdir -p /mnt/data/services/silversonic && \
    chown 1000:1000 /mnt/data/services/silversonic

WORKDIR /mnt/data/services/silversonic

# 5. Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1