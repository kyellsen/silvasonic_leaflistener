import logging
import os
import signal
import sys
import threading
import time
import types

import redis

from silvasonic_processor.db import init_db
from silvasonic_processor.indexer import Indexer
from silvasonic_processor.janitor import Janitor

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("processor")

shutdown_event = threading.Event()


def signal_handler(signum: int, frame: types.FrameType | None) -> None:
    logger.info("Shutdown signal received")
    shutdown_event.set()


def heartbeat_loop() -> None:
    redis_host = os.getenv("REDIS_HOST", "silvasonic_redis")
    try:
        r = redis.Redis(host=redis_host, port=6379, db=0, socket_timeout=5)
        import json

        import psutil

        while not shutdown_event.is_set():
            try:
                data = {
                    "service": "processor",
                    "timestamp": time.time(),
                    "status": "Running",
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                    "pid": os.getpid(),
                }
                r.set("status:processor", json.dumps(data), ex=30)
            except Exception as e:
                logger.error(f"Redis heartbeat failed: {e}")
            time.sleep(10)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Silvasonic Processor...")

    # Initialize DB
    try:
        init_db()
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Start Heartbeat
    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True, name="Heartbeat")
    heartbeat_thread.start()

    # Start Indexer Thread
    indexer = Indexer(shutdown_event)
    indexer.start()

    # Start Janitor Thread
    janitor = Janitor(shutdown_event)
    janitor.start()

    logger.info("Processor started. Waiting for work...")

    # Main loop just waits
    while not shutdown_event.is_set():
        time.sleep(1)

    logger.info("Shutting down...")
    indexer.join()
    janitor.join()
    logger.info("Goodbye.")


if __name__ == "__main__":
    main()
