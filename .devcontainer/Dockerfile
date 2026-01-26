FROM python:3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# --- WICHTIG: IDs ZUERST reservieren ---
RUN groupadd -g 999 podman && \
    groupadd -f audio

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    tree git rsync nano \
    sox ffmpeg stress \
    curl sudo lsb-release \
    podman \
    # Playwright Dependencies
    libwoff1 libopus0 libwebp7 libwebpdemux2 libenchant-2-2 \
    libsecret-1-0 libhyphen0 libgdk-pixbuf2.0-0 libegl1 \
    libnotify4 libxslt1.1 libevent-2.1-7 libgles2 libvpx7 \
    libxcomposite1 libatk1.0-0 libatk-bridge2.0-0 libepoxy0 \
    libgtk-3-0 libharfbuzz-icu0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && chmod 1777 /tmp

# 2. Install 'uv'
ENV UV_INSTALL_DIR="/usr/local/bin"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Set Workspace Directory & Permissions
# Wir bereiten den Daten-Ordner vor (damit der Mountpunkt existiert)
RUN mkdir -p /mnt/data/services/silvasonic && \
    chown 1000:1000 /mnt/data/services/silvasonic

# Code liegt hier:
WORKDIR /workspace

# 4. Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1