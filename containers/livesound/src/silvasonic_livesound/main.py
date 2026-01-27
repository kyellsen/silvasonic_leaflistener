import json
import logging
import logging.handlers
import os
import sys
import threading
import time

import psutil

os.makedirs("/var/log/silvasonic", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

try:
    file_handler = logging.handlers.TimedRotatingFileHandler(
        "/var/log/silvasonic/sound_analyser.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    logging.getLogger().addHandler(file_handler)
except Exception as e:
    logging.getLogger().warning(f"Failed to setup file logging: {e}")

logger = logging.getLogger("Main")


def write_status() -> None:
    """Writes the Livesound's own heartbeat."""
    status_file = "/mnt/data/services/silvasonic/status/livesound.json"
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    while True:
        try:
            data = {
                "service": "livesound",
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
            logger.error(f"Failed to write livesound status: {e}")

        time.sleep(5)


def main() -> None:
    logger.info("Starting Silvasonic Livesound...")

    # Start Status Thread
    t = threading.Thread(target=write_status, daemon=True)
    t.start()

    # Start Live Server (Blocking Main Process)
    logger.info("Starting Live Server (Uvicorn)...")
    import uvicorn

    # Loading via string to allow reload support if mapped, though we run direct here
    uvicorn.run("silvasonic_livesound.live.server:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
