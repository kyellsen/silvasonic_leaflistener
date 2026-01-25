import logging
import sys
from src.core.database import init_db
from src.core.watcher import WatcherService

# Setup logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("Main")

def main():
    logger.info("Starting Silvasonic Brain...")
    
    # 1. Init Database
    logger.info("Initializing Database...")
    init_db()
    
    # 2. Start Watcher (Blocking)
    logger.info("Starting Watcher Service...")
    service = WatcherService()
    service.run()

if __name__ == "__main__":
    main()
