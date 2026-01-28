#!/bin/sh
# status_reporter.sh
# Regularly queries the local Postgres instance for metrics and writes a JSON status file.

STATUS_FILE="/mnt/data/services/silvasonic/status/db.json"
TMP_STATUS_FILE="${STATUS_FILE}.tmp"
INTERVAL=30

echo "[StatusReporter] Starting loop. Target: $STATUS_FILE"

while true; do
    # Check if Postgres is accepting connections
    # -U silvasonic is default user from compose
    # -h localhost is essential as we are inside the container
    if pg_isready -U silvasonic -h 127.0.0.1 > /dev/null 2>&1; then
        
        # Determine Status
        # We query system views to get metrics
        # json_build_object requires Postgres (which is available)
        
        # Note: We use -t (tuples only) -A (no align) to get pure JSON string
        JSON_PAYLOAD=$(psql -U silvasonic -h 127.0.0.1 -d silvasonic -t -A -c "
            SELECT json_build_object(
                'status', 'healthy',
                'service', 'db',
                'last_updated_iso', to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'),
                'uptime_seconds', (EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time()))::int),
                'connections_active', (SELECT count(*) FROM pg_stat_activity WHERE state = 'active'),
                'connections_total', (SELECT count(*) FROM pg_stat_activity),
                'connections_max', (SELECT setting::int FROM pg_settings WHERE name = 'max_connections'),
                'db_size_mb', (SELECT pg_database_size('silvasonic') / 1024 / 1024)
            );
        " 2>/dev/null)
        
        if [ $? -eq 0 ] && [ ! -z "$JSON_PAYLOAD" ]; then
            echo "$JSON_PAYLOAD" > "$TMP_STATUS_FILE"
            mv "$TMP_STATUS_FILE" "$STATUS_FILE"
        else
            # DB is reachable via pg_isready but query failed (maybe starting up)
             echo "{\"status\": \"starting\", \"service\": \"db\", \"error\": \"Query failed\"}" > "$TMP_STATUS_FILE"
             mv "$TMP_STATUS_FILE" "$STATUS_FILE"
        fi

    else
        # DB not reachable
        echo "{\"status\": \"unhealthy\", \"service\": \"db\", \"error\": \"Connection refused\"}" > "$TMP_STATUS_FILE"
        mv "$TMP_STATUS_FILE" "$STATUS_FILE"
        echo "[StatusReporter] DB unreachable. Waiting..."
    fi

    sleep $INTERVAL
done
