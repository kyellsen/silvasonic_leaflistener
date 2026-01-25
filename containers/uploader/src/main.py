import os
import time
import logging
import signal
import sys
import json
from rclone_wrapper import RcloneWrapper
from janitor import StorageJanitor

# Configure Logging
os.makedirs("/var/log/silvasonic", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/silvasonic/uploader.log")
    ]
)
logger = logging.getLogger("Carrier")

# Configuration from Env
NEXTCLOUD_URL = os.getenv("UPLOADER_NEXTCLOUD_URL")
NEXTCLOUD_USER = os.getenv("UPLOADER_NEXTCLOUD_USER")
NEXTCLOUD_PASSWORD = os.getenv("UPLOADER_NEXTCLOUD_PASSWORD")
TARGET_DIR = os.getenv("UPLOADER_TARGET_DIR", "silvasonic")
SOURCE_DIR = "/data/recording"
SYNC_INTERVAL = int(os.getenv("UPLOADER_SYNC_INTERVAL", 60))
STATUS_FILE = "/var/log/silvasonic/carrier_status.json"
CLEANUP_THRESHOLD = int(os.getenv("UPLOADER_CLEANUP_THRESHOLD", 70))
CLEANUP_TARGET = int(os.getenv("UPLOADER_CLEANUP_TARGET", 60))

def write_status(status: str, last_upload: float = 0, queue_size: int = -1):
    """Write current status to JSON file for dashboard."""
    try:
        data = {
            "timestamp": time.time(),
            "status": status,
            "last_upload": last_upload,
            "queue_size": queue_size,
            "pid": os.getpid()
        }
        # Atomic write
        tmp_file = f"{STATUS_FILE}.tmp"
        with open(tmp_file, 'w') as f:
            json.dump(data, f)
        os.rename(tmp_file, STATUS_FILE)
    except Exception as e:
        logger.error(f"Failed to write status: {e}") 


def signal_handler(sig, frame):
    logger.info("Graceful shutdown received. Exiting...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("--- Silvasonic Carrier (Python Edition) ---")

    wrapper = RcloneWrapper()
    janitor = StorageJanitor(SOURCE_DIR, threshold_percent=CLEANUP_THRESHOLD, target_percent=CLEANUP_TARGET)
    
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
    last_upload_success = 0
    
    while True:
        try:
            if os.path.exists(SOURCE_DIR):
                queue_size = -1 
                
                # --- PHASE 1: UPLOAD ---
                write_status("Syncing", last_upload_success, queue_size)
                
                # Use COPY instead of SYNC to prevent deleting files on remote if they are missing locally
                wrapper.copy(SOURCE_DIR, f"remote:{TARGET_DIR}")
                
                last_upload_success = time.time()
                write_status("Idle", last_upload_success, queue_size)

                # --- PHASE 2: CLEANUP ---
                write_status("Cleaning", last_upload_success, queue_size)
                
                # Fetch remote file list for safe deletion verification
                # We do this AFTER upload to ensure the list is fresh
                remote_files = wrapper.list_files(f"remote:{TARGET_DIR}")
                
                # Run cleanup
                janitor.check_and_clean(remote_files, wrapper.get_disk_usage_percent)

            else:
                logger.error(f"Source directory {SOURCE_DIR} does not exist!")
                write_status("Error: No Source", last_upload_success)
            
            logger.info(f"Sleeping for {SYNC_INTERVAL} seconds...")
            write_status("Sleeping", last_upload_success)
            
            # Smart Sleep (interruptible)
            for _ in range(SYNC_INTERVAL):
                time.sleep(1)
                
        except Exception as e:
            logger.exception("Unexpected error in main loop:")
            time.sleep(60) # Prevent tight loop on error

if __name__ == "__main__":
    main()
