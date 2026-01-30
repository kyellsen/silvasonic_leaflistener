#!/bin/bash
set -e

# setup.sh
# Local Development Setup & Maintenance Script
# Based on docs/development.md

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function echo_task() {
    echo -e "${BLUE}▶ $1...${NC}"
}

function echo_success() {
    echo -e "${GREEN}✔ $1${NC}"
}

function echo_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function show_help() {
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "This script manages your LOCAL development environment."
    echo ""
    echo "Options:"
    echo "  --clean      Clean cleanup (remove .venv, cache, temporary files, stopped containers). Exits script."
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

# --- 1. CLEANUP (Optional) ---
if [ "$CLEAN" = true ]; then
    echo_task "Cleaning up environment"
    
    rm -rf .venv .ruff_cache .mypy_cache .pytest_cache .agent_tmp
    find . -type d -name "__pycache__" -exec rm -rf {} +
    
    echo_success "Cache and venv removed."
    
    # Optional: Podman cleanup
    if command -v podman &> /dev/null; then
         echo_task "Pruning stopped containers"
         podman container prune -f
    fi

    echo_success "Cleanup complete. Run ./setup.sh without --clean to setup environment."
    exit 0
fi

# --- 2. DEPENDENCIES (uv) ---
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' is not installed.${NC}"
    echo "Install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo_task "Syncing dependencies (uv)"
uv sync
echo_success "Dependencies synced."

# --- 3. CONFIGURATION (.env) ---
if [ ! -f ".env" ]; then
    echo_task "Creating .env from config.example.env"
    cp config.example.env .env
    echo_warn "Created .env file. Please check and update it with your secrets!"
else
    echo_success ".env file exists."
fi

# --- 4. DATA DIRECTORIES ---
# Load .env variables (if present) to find SILVASONIC_DATA_DIR
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default to local dev path if not set (Safe default for workstation)
target_data_dir=${SILVASONIC_DATA_DIR:-/mnt/data/dev_workspaces/silvasonic}

echo_task "Verifying data directories at $target_data_dir"

# 1. Ensure BASE Directory exists and is owned by user
if [ ! -d "$target_data_dir" ]; then
    echo_task "Creating base directory: $target_data_dir"
    if mkdir -p "$target_data_dir" 2>/dev/null; then
         :
    else
         echo_warn "Using sudo to create base directory"
         sudo mkdir -p "$target_data_dir"
         # CRITICAL: Fix ownership of the entire base immediately
         sudo chown -R $USER:$USER "$target_data_dir"
    fi
fi

# 2. Define critical sub-paths
REQUIRED_DIRS=(
    "$target_data_dir/recorder/recordings"
    "$target_data_dir/logs"
    "$target_data_dir/status"
    "$target_data_dir/uploader/config"
    "$target_data_dir/errors"
    "$target_data_dir/config"
    "$target_data_dir/notifications"
    "$target_data_dir/birdnet/results"
    "$target_data_dir/db/data"
)

# 3. Create subdirectories (should now work without sudo if base is correct)
for DIR in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$DIR" ]; then
        if mkdir -p "$DIR" 2>/dev/null; then
             :
        else
             # Fail if we still can't write, to avoid partial root ownership mess
             echo_warn "Cannot create $DIR as current user."
             echo_warn "Fixing permissions on $target_data_dir and retrying..."
             sudo chown -R $USER:$USER "$target_data_dir"
             mkdir -p "$DIR"
        fi
    fi
done
echo_success "Data directories verified."


# --- 5. CONTAINER MANAGEMENT ---
if [ "$REBUILD" = true ]; then
    echo_task "Rebuilding containers"
    
    if command -v podman-compose &> /dev/null; then
        # Ensure we have a valid .env before starting
        podman-compose down || true
        podman-compose up -d --build
        echo_success "Containers rebuilt and started."
    else
        echo -e "${RED}Error: podman-compose not found.${NC}"
        exit 1
    fi
fi

# --- 6. SUMMARY ---
echo ""
echo -e "${GREEN}✨ Development Environment Ready!${NC}"
echo "---------------------------------------------------"
echo "To activate venv:   ${YELLOW}source .venv/bin/activate${NC}"
echo "To run tests:       ${YELLOW}uv run pytest${NC}"
echo "To start stack:     ${YELLOW}podman-compose up -d${NC}"
echo "---------------------------------------------------"
