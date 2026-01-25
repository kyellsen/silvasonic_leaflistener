import os
import time
import logging
import signal
import sys
import json
import psutil
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
STATUS_FILE = "/mnt/data/services/silvasonic/status/carrier.json"
ERROR_DIR = "/mnt/data/services/silvasonic/errors"
CLEANUP_THRESHOLD = int(os.getenv("UPLOADER_CLEANUP_THRESHOLD", 70))
CLEANUP_TARGET = int(os.getenv("UPLOADER_CLEANUP_TARGET", 60))
MIN_AGE = os.getenv("UPLOADER_MIN_AGE", "1m")

# Ensure directories exist
os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
os.makedirs(ERROR_DIR, exist_ok=True)

def write_status(status: str, last_upload: float = 0, queue_size: int = -1):
    """Write current status to JSON file for dashboard."""
    try:
        data = {
            "service": "carrier",
            "timestamp": time.time(),
            "status": status,
            "cpu_percent": psutil.cpu_percent(),
            "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
            "meta": {
                "last_upload": last_upload,
                "queue_size": queue_size
            },
            "last_upload": last_upload, # Keeping top-level for backwards compat if needed temporarily, but dashboard should update
            "pid": os.getpid()
        }
        # Atomic write
        tmp_file = f"{STATUS_FILE}.tmp"
        with open(tmp_file, 'w') as f:
            json.dump(data, f)
        os.rename(tmp_file, STATUS_FILE)
    except Exception as e:
        logger.error(f"Failed to write status: {e}") 

def report_error(context: str, error: Exception):
    """Write critical error to shared error directory for the Watchdog."""
    try:
        timestamp = int(time.time())
        filename = f"{ERROR_DIR}/error_carrier_{timestamp}.json"
        
        data = {
            "service": "carrier",
            "timestamp": timestamp,
            "context": context,
            "error": str(error),
            "pid": os.getpid()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f)
            
        logger.error(f"Critical error reported to {filename}")
    except Exception as ie:
         logger.error(f"Failed to report error: {ie}") 


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
                # Use MIN_AGE to avoid uploading files currently being written by the recorder
                success = wrapper.copy(SOURCE_DIR, f"remote:{TARGET_DIR}", min_age=MIN_AGE)
                
                if success:
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
                    logger.error("Upload failed. Validation and cleanup skipped.")
                    write_status("Error: Upload Failed", last_upload_success, queue_size)
                    # We don't write an explicit error file for transient network errors,
                    # we rely on the watchdog spotting the stale 'last_upload' timestamp.

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
            report_error("main_loop_crash", e)
            write_status("Error: Crashed", last_upload_success)
            time.sleep(60) # Prevent tight loop on error

if __name__ == "__main__":
    main()
