import json
import os
import time

import psutil
import redis
import structlog

logger = structlog.get_logger()


def write_status() -> None:
    """Writes the Dashboard's own heartbeat to Redis."""
    logger.info("Starting Dashboard Redis Heartbeat")

    # Lazy connect
    r: redis.Redis | None = None

    while True:
        try:
            if r is None:
                r = redis.Redis(host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=2)

            data = {
                "service": "dashboard",
                "timestamp": time.time(),
                "status": "Running",
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "pid": os.getpid(),
            }

            r.setex("status:dashboard", 10, json.dumps(data))

        except Exception as e:
            logger.error("Failed to write dashboard status to Redis", error=str(e))
            r = None

        time.sleep(5)  # Check every 5s
