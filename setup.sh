#!/bin/bash
set -e

# setup.sh
# Central Setup & Maintenance Script for Silvasonic
# Based on docs/DEVELOPMENT.md

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function echo_task() {
    echo -e "${BLUE}🔨 $1...${NC}"
}

function echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function echo_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function show_help() {
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --clean      Clean cleanup (remove .venv, cache, temporary files)"
    echo "  --rebuild    Rebuild containers (podman-compose build)"
    echo "  --help       Show this help message"
    echo ""
    echo "Default behavior: Install dependencies (uv sync), setup .env, and prepare environment."
}

CLEAN=false
REBUILD=false

# Argument Parsing
for arg in "$@"; do
    case $arg in
        --clean)
            CLEAN=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            show_help
            exit 1
            ;;
    esac
done

if [ "$CLEAN" = true ]; then
    echo -e "${RED}🧹 Cleaning up environment...${NC}"
    
    if [ -d ".venv" ]; then
        echo "Removing .venv..."
        rm -rf .venv
    fi
    
    if [ -d ".ruff_cache" ]; then
        rm -rf .ruff_cache
    fi
    
    if [ -d ".mypy_cache" ]; then
        rm -rf .mypy_cache
    fi
    
    if [ -d ".pytest_cache" ]; then
        rm -rf .pytest_cache
    fi
    
    # Optional: Clean podman resources if desired, but maybe too aggressive for default check?
    # Keeping it to local dev files for now.
    
    echo_success "Cleanup complete."
fi

# 1. Check for 'uv'
if ! command -v uv &> /dev/null; then
    echo_warn "'uv' not found!"
    echo "   Please install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo_success "'uv' is installed."

# 2. Virtual Environment & Dependencies
echo_task "Syncing dependencies with uv"
uv sync
echo_success "Dependencies synced."

# 3. Configuration (.env)
if [ ! -f ".env" ]; then
    echo_task "Creating .env from config.example.env"
    cp config.example.env .env
    echo_warn "Created .env file. Please check and update it with your secrets/settings!"
else
    echo_success ".env file exists."
fi

# 3.5 Data Directories (Volumes)
# Load .env variables if present
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default to production path if not set
SILVASONIC_DATA_DIR=${SILVASONIC_DATA_DIR:-/mnt/data/services/silvasonic}

echo_task "Ensuring required data directories exist at ${SILVASONIC_DATA_DIR}..."
REQUIRED_DIRS=(
    "${SILVASONIC_DATA_DIR}/recorder/recordings"
    "${SILVASONIC_DATA_DIR}/logs"
    "${SILVASONIC_DATA_DIR}/status"
    "${SILVASONIC_DATA_DIR}/uploader/config"
    "${SILVASONIC_DATA_DIR}/errors"
    "${SILVASONIC_DATA_DIR}/config"
    "${SILVASONIC_DATA_DIR}/notifications"
    "${SILVASONIC_DATA_DIR}/birdnet/results"
    "${SILVASONIC_DATA_DIR}/db/data"
)

for DIR in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$DIR" ]; then
        echo "Creating $DIR..."
        mkdir -p "$DIR"
    fi
done
echo_success "Data directories verified."

# 4. Container Management (if requested)
if [ "$REBUILD" = true ]; then
    echo_task "Rebuilding containers (podman-compose)"
    if command -v podman-compose &> /dev/null; then
        podman-compose down
        podman-compose up -d --build
        echo_success "Containers rebuilt and started."
    else
        echo_warn "podman-compose not found. Skipping container rebuild."
    fi
fi

# 5. Final Report & Recommendations
echo ""
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo "---------------------------------------------------"
echo "Recommended Next Steps:"
echo "1. Activate Virtual Env:  ${YELLOW}source .venv/bin/activate${NC}"
echo "2. Run Code Checks:       ${YELLOW}./scripts/run_checks.sh${NC}"
echo "3. Start Services:        ${YELLOW}podman-compose up -d${NC}"
echo "4. View Logs:             ${YELLOW}podman-compose logs -f${NC}"
echo ""
echo "Development Workflow:"
echo "- To run tests:           ${YELLOW}uv run pytest${NC}"
echo "- To restart a service:   ${YELLOW}podman-compose restart <service_name>${NC}"
echo "---------------------------------------------------"
