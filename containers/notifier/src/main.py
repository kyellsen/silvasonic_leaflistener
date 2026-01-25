import os
import time
import json
import glob
import logging
import sys
import shutil
from mailer import Mailer

# Logging Config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Watchdog")

# Config
BASE_DIR = "/mnt/data/services/silvasonic"
STATUS_FILE = f"{BASE_DIR}/status/carrier.json"
ERROR_DIR = f"{BASE_DIR}/errors"
ARCHIVE_DIR = f"{BASE_DIR}/errors/archive"
CHECK_INTERVAL = 60 # Check every minute
STALE_THRESHOLD = 60 * 60 # 60 minutes

def ensure_dirs():
    os.makedirs(ERROR_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

def check_carrier_status(mailer: Mailer):
    """Checks if the carrier is stale (hasn't uploaded in > 60 mins)."""
    if not os.path.exists(STATUS_FILE):
        # Allow some grace period on startup, but eventually alarm? 
        # For now, just log warning.
        logger.warning(f"Carrier status file not found at {STATUS_FILE}")
        return

    try:
        with open(STATUS_FILE, 'r') as f:
            status = json.load(f)
        
        last_upload = status.get('last_upload', 0)
        current_time = time.time()
        
        # If last_upload is 0, it might be a fresh start.
        if last_upload == 0:
            return

        time_since_upload = current_time - last_upload
        
        if time_since_upload > STALE_THRESHOLD:
            # Check if we already alerted recently to avoid spam (optional improvement)
            # For now, simplistic check.
            msg = f"Carrier has not uploaded successfully for {int(time_since_upload / 60)} minutes.\n\nLatest Status: {json.dumps(status, indent=2)}"
            logger.error(msg)
            mailer.send_alert("Carrier Stalled", msg)
            
    except Exception as e:
        logger.error(f"Failed to read carrier status: {e}")

def check_error_drops(mailer: Mailer):
    """Checks for new files in the error drop directory."""
    error_files = glob.glob(f"{ERROR_DIR}/*.json")
    
    if not error_files:
        return

    for err_file in error_files:
        try:
            with open(err_file, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Processing error file: {err_file}")
            
            subject = f"Critical Error in {data.get('service', 'Unknown Service')}"
            body = f"Context: {data.get('context')}\nError: {data.get('error')}\nTimestamp: {data.get('timestamp')}\n\nFull Dump:\n{json.dumps(data, indent=2)}"
            
            if mailer.send_alert(subject, body):
                # Move to archive only on success
                filename = os.path.basename(err_file)
                shutil.move(err_file, os.path.join(ARCHIVE_DIR, filename))
            
        except Exception as e:
            logger.error(f"Failed to process error file {err_file}: {e}")

def main():
    logger.info("--- Silvasonic Watchdog Started ---")
    ensure_dirs()
    mailer = Mailer()
    
    while True:
        try:
            check_carrier_status(mailer)
            check_error_drops(mailer)
        except Exception as e:
            logger.exception("Watchdog loop crashed:")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
