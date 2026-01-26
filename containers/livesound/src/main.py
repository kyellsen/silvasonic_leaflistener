import logging
import logging.handlers
import sys
import os
import time
import json
import threading
import psutil


os.makedirs("/var/log/silvasonic", exist_ok=True)

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

def write_status():
    """Writes the Livesound's own heartbeat."""
    STATUS_FILE = "/mnt/data/services/silvasonic/status/livesound.json"
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    
    while True:
        try:
            data = {
                "service": "livesound",
                "timestamp": time.time(),
                "status": "Running",
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "pid": os.getpid()
            }
            
            tmp_file = f"{STATUS_FILE}.tmp"
            with open(tmp_file, 'w') as f:
                json.dump(data, f)
            os.rename(tmp_file, STATUS_FILE)
        except Exception as e:
            logger.error(f"Failed to write livesound status: {e}")
            
        time.sleep(15)

def main():
    logger.info("Starting Silvasonic Livesound...")
    
    # Start Status Thread
    t = threading.Thread(target=write_status, daemon=True)
    t.start()

    # Start Live Server (Blocking Main Process)
    logger.info("Starting Live Server (Uvicorn)...")
    import uvicorn
    # Loading via string to allow reload support if mapped, though we run direct here
    uvicorn.run("src.live.server:app", host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
