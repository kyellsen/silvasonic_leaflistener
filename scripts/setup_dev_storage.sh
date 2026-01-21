#!/bin/bash
# scripts/setup_dev_storage.sh
# Ensures the local development storage directory exists and has correct permissions.

STORAGE_DIR="/mnt/data/dev_workspaces/silvasonic_leaflistner/raw"

echo "Setting up development storage at $STORAGE_DIR..."

if [ ! -d "$STORAGE_DIR" ]; then
    echo "Creating directory..."
    mkdir -p "$STORAGE_DIR"
else
    echo "Directory already exists."
fi

# Ensure current user owns it (important for rootless podman/docker)
# We assume the script is run by the user who runs podman
# If run as sudo, this might need adjustment, but for dev it should be fine.
# chmod 777 might be overkill, but ensures the container (running as root or other) can write.
# Better approach: rely on :z in podman-compose for SELinux and standard permissions.
# But let's verify write access.

if [ -w "$STORAGE_DIR" ]; then
    echo "Directory is writable."
else
    echo "Warning: Directory might not be writable by current user."
fi

echo "Storage setup complete."
