#!/bin/bash
# scripts/teardown.sh
# Stops containers and optionally cleans up recorded data.

set -e

COMPOSE_FILE="podman-compose.dev.yml"
STORAGE_DIR="/mnt/data/dev_workspaces/silvasonic_leaflistner/raw"

echo "Stopping containers..."
podman-compose -f "$COMPOSE_FILE" down

echo "Containers stopped."

read -p "Do you want to delete all recorded data in $STORAGE_DIR? (y/N) " confirm

if [[ "$confirm" =~ ^[Yy]$ ]]; then
    if [ -d "$STORAGE_DIR" ]; then
        echo "Cleaning up data..."
        rm -rf "${STORAGE_DIR:?}"/*
        echo "Data deleted."
    else
        echo "Directory $STORAGE_DIR does not exist, nothing to clean."
    fi
else
    echo "Data cleanup skipped."
fi

echo "Teardown complete."
