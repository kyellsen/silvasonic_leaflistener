import os
import time
import logging
import signal
import sys
from rclone_wrapper import RcloneWrapper

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Carrier")

# Configuration from Env
NEXTCLOUD_URL = os.getenv("UPLOADER_NEXTCLOUD_URL")
NEXTCLOUD_USER = os.getenv("UPLOADER_NEXTCLOUD_USER")
NEXTCLOUD_PASSWORD = os.getenv("UPLOADER_NEXTCLOUD_PASSWORD")
TARGET_DIR = os.getenv("UPLOADER_TARGET_DIR", "silvasonic")
SOURCE_DIR = "/data/recording"
SYNC_INTERVAL = 3600  # 1 Hour

def signal_handler(sig, frame):
    logger.info("Graceful shutdown received. Exiting...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("--- Silvasonic Carrier (Python Edition) ---")

    wrapper = RcloneWrapper()
    
    # 1. Configuration Check
    if NEXTCLOUD_URL and NEXTCLOUD_USER and NEXTCLOUD_PASSWORD:
        wrapper.configure_webdav(
            remote_name="remote",
            url=NEXTCLOUD_URL,
            user=NEXTCLOUD_USER,
            password=NEXTCLOUD_PASSWORD
        )
    else:
        logger.warning("Environment variables missing. Assuming config file already exists.")

    # 2. Main Loop
    while True:
        try:
            if os.path.exists(SOURCE_DIR):
                wrapper.sync(SOURCE_DIR, f"remote:{TARGET_DIR}")
            else:
                logger.error(f"Source directory {SOURCE_DIR} does not exist!")
            
            logger.info(f"Sleeping for {SYNC_INTERVAL} seconds...")
            
            # Smart Sleep (interruptible)
            for _ in range(SYNC_INTERVAL):
                time.sleep(1)
                
        except Exception as e:
            logger.exception("Unexpected error in main loop:")
            time.sleep(60) # Prevent tight loop on error

if __name__ == "__main__":
    main()
