#!/bin/bash
set -e

# Copy staged assets to the mounted source directory
# This ensures that even if local source is mounted over /app/src,
# the built assets are restored.

echo "Restoring built assets..."

# Ensure target directories exist
mkdir -p /app/src/silvasonic_dashboard/static/css
mkdir -p /app/src/static/js

# Copy CSS
if [ -f /app/assets_dist/styles.css ]; then
    echo "Copying styles.css to /app/src/silvasonic_dashboard/static/css/"
    cp /app/assets_dist/styles.css /app/src/silvasonic_dashboard/static/css/styles.css
else
    echo "WARNING: /app/assets_dist/styles.css not found!"
fi

# Copy JS (Plotly)
if [ -f /app/assets_dist/plotly.min.js ]; then
    echo "Copying plotly.min.js to /app/src/static/js/"
    cp /app/assets_dist/plotly.min.js /app/src/static/js/plotly.min.js
else
    echo "WARNING: /app/assets_dist/plotly.min.js not found!"
fi

# Execute the passed command
exec "$@"
