#!/bin/bash
set -e

echo "--- Silvasonic DevContainer Setup ---"

# 1. Fix Permissions
sudo chown -R vscode:vscode /workspace

# 2. Sync Dependencies using UV
echo "Installing dependencies with uv..."
uv sync --all-extras

# 3. Install Playwright Browsers (needed for some tests)
if [[ -f ".venv/bin/playwright" ]]; then
    echo "Installing Playwright browsers..."
    uv run playwright install --with-deps chromium
fi

# 4. Add vscode user to audio group (runtime fix)
sudo usermod -aG audio vscode

echo "--- Setup Complete! ---"
echo "You are running on $(uname -m) architecture."
echo "If this is 'aarch64', you are successfully emulating the Raspberry Pi environment."
