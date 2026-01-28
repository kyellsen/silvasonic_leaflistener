#!/bin/bash
set -e

# Navigate to the project root
cd "$(dirname "$0")/.."

# Run pytest with coverage options targeting the containers directory
# --cov=containers: Target the containers directory for coverage
# --cov-report=term-missing: Show lines missing coverage in the terminal
# --cov-report=html:cov_html: Generate an HTML coverage report in the cov_html directory
echo "Running pytest with coverage..."
uv run pytest --cov=containers --cov-report=term-missing --cov-report=html:cov_html "$@"
