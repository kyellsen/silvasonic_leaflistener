#!/bin/bash
set -e

echo "--- Silvasonic DevContainer Setup (Native) ---"

# 1. Fix Permissions
sudo chown -R vscode:vscode /mnt/data/services/silversonic

# 2. Sync Dependencies using UV
echo "Installing dependencies with uv..."
uv sync --all-extras

# 3. Install Playwright Browsers
if [[ -f ".venv/bin/playwright" ]]; then
    echo "Installing Playwright browsers..."
    uv run playwright install --with-deps chromium
fi

# 4. Add vscode user to audio group
sudo usermod -aG audio vscode

echo "--- Setup Complete! ---"
echo "Running natively on: $(uname -m)"