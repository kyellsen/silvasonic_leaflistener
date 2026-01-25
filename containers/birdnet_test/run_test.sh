#!/bin/bash
set -e

# Define paths
PROJECT_ROOT=$(pwd | sed 's|containers/birdnet_test||') # Assuming we might run from subdir, but let's be safer
# Actually, let's assume we run this script FROM the containers/birdnet_test directory or we handle it relative to where it is.
# Best practice: script locates itself.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")" # Go up two levels: containers/birdnet_test -> containers -> packages/silvasonic

echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

echo "Building BirdNET Test Container..."
docker build -f containers/birdnet_test/Dockerfile -t birdnet_test .

echo "Running BirdNET Test Container..."
mkdir -p "$SCRIPT_DIR/results" # Ensure local results dir exists

docker run --rm \
    -v "$SCRIPT_DIR/test_data":/app/test_data:z \
    -v "$SCRIPT_DIR/results":/data/db/results:z \
    birdnet_test
