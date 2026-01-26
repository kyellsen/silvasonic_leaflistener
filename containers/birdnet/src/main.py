import logging

# Setup logging to stdout
import logging.handlers
import sys
import os

from src.watcher import WatcherService

os.makedirs("/var/log/silvasonic", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.TimedRotatingFileHandler(
            "/var/log/silvasonic/birdnet.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger("Main")

def main():
    logger.info("Starting Silvasonic BirdNET (Ornithologist)...")

    # Start Watcher (Blocking)
    logger.info("Starting Watcher Service...")
    service = WatcherService()
    service.run()

if __name__ == "__main__":
    main()
