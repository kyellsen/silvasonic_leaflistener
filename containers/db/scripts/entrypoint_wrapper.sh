#!/bin/sh
# entrypoint_wrapper.sh
# Wraps the original postgres start command to launch our status reporter in background.

# 1. Start the status reporter in background
/scripts/status_reporter.sh &
PID_REPORTER=$!

echo "[Wrapper] Started Status Reporter with PID $PID_REPORTER"

# 2. Execute the original Docker Command (passed as arguments to this script)
#    Usually this is: "postgres -c config_file=..."
#    We use 'exec' so postgres takes over PID 1 (or the shell gets out of the way),
#    but since we have a background job, we want this shell to stay alive if we want to manage signals.
#    However, the cleanest way in Docker is usually to let the main process take over.
#    BUT: If we exec, the background process might be orphaned or killed depending on implementation.
#    Simple approach: Just run the command. PostgreSQL image entrypoint usually handles the rest.
#    CAUTION: The "command" in docker-compose overrides the CMD, but NOT the ENTRYPOINT.
#    The Postgres image has a complex ENTRYPOINT script that does setup.
#    We are overriding CMD. So we just need to exec what was passed.

echo "[Wrapper] Executing original command: $@"
exec "$@"
