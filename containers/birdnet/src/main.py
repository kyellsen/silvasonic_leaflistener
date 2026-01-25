import logging
import sys
from src.watcher import WatcherService

# Setup logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/silvasonic/birdnet.log")
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
