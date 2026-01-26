FROM python:3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# --- WICHTIG: IDs ZUERST reservieren ---
# Wir legen die Gruppen an, BEVOR wir Pakete installieren.
# So verhindern wir, dass apt-get sich die ID 1000 schnappt.
RUN groupadd -g 999 podman && \
    groupadd -f audio

# 1. Install System Dependencies
# Jetzt können wir podman installieren, es wird die existierende Gruppe (999) nutzen.
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

# 3. Set Workspace Directory & Permissions
# Wir bereiten den Ordner vor. chown 1000:1000 funktioniert auch,
# wenn der User 'vscode' erst später durch das Feature erstellt wird.
RUN mkdir -p /mnt/data/services/silversonic && \
    chown 1000:1000 /mnt/data/services/silversonic

WORKDIR /mnt/data/services/silversonic

# 4. Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1