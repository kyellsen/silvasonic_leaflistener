FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

# Install additional OS packages.
# libsndfile1: Required for soundfile (audio processing)
# ffmpeg: Required for audio conversion/resampling
# alsa-utils: Useful for audio device query/testing
# podman: For container management within devcontainer
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    alsa-utils \
    podman \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
