#!/bin/bash
set -e

echo "Setting up development environment..."

# Create local data directory structure if it doesn't exist
# This ensures that the environment variables point to valid directories
mkdir -p data/recording
mkdir -p data/db
mkdir -p data/processed/artifacts
mkdir -p data/processed/metadata

echo "Created local data directories in ./data"

# Sync dependencies using uv
echo "Syncing dependencies..."
uv sync

echo "Setup complete!"
