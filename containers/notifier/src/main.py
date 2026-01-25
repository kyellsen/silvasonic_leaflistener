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
SERVICES_CONFIG = {
    "carrier": {"name": "Carrier (Uploader)", "timeout": 3600}, # 60 mins
    "recorder": {"name": "Recorder", "timeout": 120}, # 2 mins
    "birdnet": {"name": "BirdNET", "timeout": 300}, # 5 mins
    "sound_analyser": {"name": "Brain", "timeout": 300} # 5 mins
}

STATUS_DIR = f"{BASE_DIR}/status"

def check_services_status(mailer: Mailer):
    """Checks status files for all configured services."""
    current_time = time.time()
    
    for service_id, config in SERVICES_CONFIG.items():
        status_file = f"{STATUS_DIR}/{service_id}.json"
        
        if not os.path.exists(status_file):
            logger.warning(f"Status file missing for {config['name']} ({status_file})")
            continue
            
        try:
            with open(status_file, 'r') as f:
                status = json.load(f)
                
            last_ts = status.get('timestamp', 0)
            
            # Special logic for Carrier (it reports 'last_upload' too, but use heartbeat for liveness)
            # Actually, for carrier we specifically cared about 'last_upload' success.
            # But here we check *liveness* of the process first.
            if current_time - last_ts > config['timeout']:
                msg = f"Service {config['name']} is silent. No heartbeat for {int(current_time - last_ts)} seconds.\nTimeout is {config['timeout']}s."
                logger.error(msg)
                mailer.send_alert(f"{config['name']} Down", msg)
                
            # Secondary check for Carrier: Upload success
            if service_id == "carrier":
                 last_upload = status.get('last_upload', 0) 
                 # Note: Uploader main.py puts it in 'meta' maybe, or top level? 
                 # We kept it top level for compat in previous edit.
                 if current_time - last_upload > 3600: # 60 mins
                      msg = f"Carrier running but no upload success for > 60 mins."
                      # Check if we already alerted? (Simplified for now)
                      logger.error(msg)
                      mailer.send_alert("Carrier Stalled", msg)

        except Exception as e:
            logger.error(f"Failed to check status for {service_id}: {e}")

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
            check_services_status(mailer)
            check_error_drops(mailer)
        except Exception as e:
            logger.exception("Watchdog loop crashed:")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
