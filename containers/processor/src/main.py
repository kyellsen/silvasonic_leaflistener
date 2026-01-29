import logging
import os
import signal
import sys
import threading
import time

import redis
from src.db import init_db
from src.indexer import Indexer
from src.janitor import Janitor

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("processor")

shutdown_event = threading.Event()


def signal_handler(signum, frame):
    logger.info("Shutdown signal received")
    shutdown_event.set()


def heartbeat_loop():
    redis_host = os.getenv("REDIS_HOST", "silvasonic_redis")
    try:
        r = redis.Redis(host=redis_host, port=6379, db=0, socket_timeout=5)
        while not shutdown_event.is_set():
            try:
                r.set("status:processor:heartbeat", int(time.time()), ex=30)
            except Exception as e:
                logger.error(f"Redis heartbeat failed: {e}")
            time.sleep(10)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")


def main():
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
