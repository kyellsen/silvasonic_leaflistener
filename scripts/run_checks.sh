#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo "🛡️  Starting Code Quality Checks..."
echo "================================="

# Helper function
run_cmd() {
    echo -e "${BLUE}▶ $1${NC}"
    eval "$1"
}

# 1. Ruff Formatting
run_cmd "uv run ruff format ."

# 2. Ruff Linting
run_cmd "uv run ruff check --fix ."

# 3. MyPy Type Checking
# Explicitly checking source dirs to avoid .venv issues
run_cmd "uv run mypy containers scripts tools"

# 4. Pytest (Root)
echo -e "${BLUE}▶ pytest${NC}"
uv run pytest

echo -e "${GREEN}✅ All checks passed!${NC}"
