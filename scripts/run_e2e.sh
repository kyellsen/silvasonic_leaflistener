#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Default values
TARGET_URL="http://localhost:8080"
E2E_DIR="tests/e2e"
HEADED=false

# Help function
show_help() {
    echo "Usage: ./scripts/run_e2e.sh [options]"
    echo ""
    echo "Options:"
    echo "  --headed        Run tests in headed mode (visible browser)"
    echo "  --url <url>     Target specific URL (default: http://localhost:8080)"
    echo "  --help          Show this help message"
    echo ""
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --headed) HEADED=true ;;
        --url) TARGET_URL="$2"; shift ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; show_help; exit 1 ;;
    esac
    shift
done

echo -e "${BLUE}🛡️  Starting E2E Tests against ${TARGET_URL}...${NC}"

# Check if target is reachable
echo -e "${BLUE}▶ Checking connectivity...${NC}"
if ! curl -s --head --request GET "${TARGET_URL}" > /dev/null; then
    echo -e "${RED}❌ Error: Cannot reach ${TARGET_URL}${NC}"
    echo -e "${RED}Please ensure your stack is running (e.g., podman compose up)${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Target is reachable${NC}"

# Build pytest arguments
PYTEST_ARGS=("$E2E_DIR")
if [ "$HEADED" = true ]; then
    PYTEST_ARGS+=("--headed")
fi

# Pass base url via env var or pytest arg if we set up pytest-base-url plugin,
# but since we are using a custom fixture/conftest, we'll pass it via env var usually, 
# or just rely on the test picking it up. 
# However, standard practice with playwright-pytest is often just `pytest --base-url ...` if using the plugin,
# OR we can pass it as an environment variable that our conftest reads.
# Let's use an environment variable for simplicity in our custom conftest.
echo -e "${BLUE}▶ Running Pytest...${NC}"
export E2E_BASE_URL="$TARGET_URL"
uv run pytest "${PYTEST_ARGS[@]}"
