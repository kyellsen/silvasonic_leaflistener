#!/bin/bash
set -e

# setup.sh
# Bootstrap script for Silvasonic Development
# Establishes the canonical environment using 'uv'.

echo "🌱 Silvasonic Development Setup"
echo "=============================="

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ 'uv' not found. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ 'uv' found."

# Create/Sync Virtual Environment
echo "🔄 Syncing dependencies..."
uv sync

echo "✅ Setup complete."
echo "   Activate env: source .venv/bin/activate"
