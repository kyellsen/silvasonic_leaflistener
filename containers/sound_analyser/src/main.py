import logging

# Setup logging to stdout
import logging.handlers
import sys
import threading

from src.core.database import init_db
from src.core.watcher import WatcherService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.TimedRotatingFileHandler(
            "/var/log/silvasonic/sound_analyser.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger("Main")

def main():
    logger.info("Starting Silvasonic Brain...")

    # 1. Init Database
    logger.info("Initializing Database...")
    init_db()

    # 2. Start Watcher (Daemon Thread)
    logger.info("Starting Watcher Service in background...")
    watcher = WatcherService()
    watcher_thread = threading.Thread(target=watcher.run, daemon=True)
    watcher_thread.start()

    # 3. Start Live Server (Blocking Main Process)
    logger.info("Starting Live Server (Uvicorn)...")
    import uvicorn
    # Loading via string to allow reload support if mapped, though we run direct here
    uvicorn.run("src.live.server:app", host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
