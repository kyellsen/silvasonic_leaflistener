#!/bin/bash
# set -e  <-- Removed to allow startup even if asset copy fails

# Copy staged assets to the mounted source directory
# This ensures that even if local source is mounted over /app/src,
# the built assets are restored.

echo "Restoring built assets..."

# Ensure target directories exist
mkdir -p /app/src/silvasonic_dashboard/static/css || echo "WARNING: Failed to create css dir"
mkdir -p /app/src/static/js || echo "WARNING: Failed to create js dir"

# Copy CSS
if [ -f /app/assets_dist/styles.css ]; then
    echo "Copying styles.css to /app/src/silvasonic_dashboard/static/css/"
    cp /app/assets_dist/styles.css /app/src/silvasonic_dashboard/static/css/styles.css || echo "WARNING: Failed to copy styles.css (Permissions?)"
else
    echo "WARNING: /app/assets_dist/styles.css not found!"
fi

# Copy JS (Plotly)
if [ -f /app/assets_dist/plotly.min.js ]; then
    echo "Copying plotly.min.js to /app/src/static/js/"
    cp /app/assets_dist/plotly.min.js /app/src/static/js/plotly.min.js || echo "WARNING: Failed to copy plotly.min.js (Permissions?)"
else
    echo "WARNING: /app/assets_dist/plotly.min.js not found!"
fi

# Execute the passed command
exec "$@"
