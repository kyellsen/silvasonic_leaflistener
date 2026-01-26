#!/bin/bash
set -e

# run_checks.sh
# Run code quality tools and tests for Silvasonic
# Includes: Ruff (Lint/Format), MyPy (Types), Pytest (Tests)

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

function run_step() {
    echo -e "${BLUE}▶ Running: $1${NC}"
    $1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✔ Success${NC}\n"
    else
        echo -e "${RED}✘ Failed${NC}"
        exit 1
    fi
}

echo "🛡️  Starting Code Quality Checks..."
echo "================================="

# 1. Ruff Formatting (Check only, or fix?)
# User asked for "ruff check --fix", usually one wants to format too.
# Let's run format first to ensure style is correct.
echo -e "${BLUE}▶ ruff format .${NC}"
uv run ruff format .

# 2. Ruff Linting (with fix)
# This will fix simple issues and report others.
echo -e "${BLUE}▶ ruff check --fix .${NC}"
uv run ruff check --fix .

# 3. MyPy Type Checking
echo -e "${BLUE}▶ mypy .${NC}"
uv run mypy .

# 4. Pytest (Root)
# Runs tests found in /tests/ or standard locations
echo -e "${BLUE}▶ pytest${NC}"
uv run pytest

echo "================================="
echo -e "${GREEN}✨ All checks passed! Ready to commit.${NC}"
