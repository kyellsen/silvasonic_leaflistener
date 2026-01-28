import json
import os
import time

import psutil
import structlog

logger = structlog.get_logger()


def write_status() -> None:
    """Writes the Dashboard's own heartbeat."""
    status_file = "/mnt/data/services/silvasonic/status/dashboard.json"
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    logger.info("Starting Dashboard Heartbeat")

    while True:
        try:
            data = {
                "service": "dashboard",
                "timestamp": time.time(),
                "status": "Running",
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "pid": os.getpid(),
            }

            tmp_file = f"{status_file}.tmp"
            with open(tmp_file, "w") as f:
                json.dump(data, f)
            os.rename(tmp_file, status_file)
        except Exception as e:
            logger.error("Failed to write dashboard status", error=str(e))

        time.sleep(5)  # Check every 5s
