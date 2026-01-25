import time
import logging
import subprocess
import os
import signal
from wifi_manager import WifiManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wifi_monitor")

class WifiMonitor:
    def __init__(self):
        self.manager = WifiManager()
        self.flask_process = None
        self.ap_active = False
        self.check_interval = 10 # Check every 10 seconds
        self.disconnection_counter = 0
        self.disconnection_threshold = 3 # 3 checks = 30 seconds wait before AP

    def start_flask(self):
        if self.flask_process is None:
            logger.info("Starting Web Config Portal...")
            # Run flask app as a subprocess
            env = os.environ.copy()
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
            self.flask_process = subprocess.Popen(
                ["python3", script_path],
                env=env,
                preexec_fn=os.setsid # Create new session group for easy killing
            )

    def stop_flask(self):
        if self.flask_process:
            logger.info("Stopping Web Config Portal...")
            try:
                os.killpg(os.getpgid(self.flask_process.pid), signal.SIGTERM)
                self.flask_process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error killing flask: {e}")
            self.flask_process = None

    def run(self):
        logger.info("WiFi Monitor Service Started")
        
        # Initial wait to let boot finish and existing connections establish
        time.sleep(15) 

        while True:
            try:
                connected = self.manager.is_connected()
                
                if connected:
                    logger.debug("System online.")
                    self.disconnection_counter = 0
                    
                    if self.ap_active:
                        logger.info("Connection detected! Stopping AP mode.")
                        self.manager.stop_ap()
                        self.stop_flask()
                        self.ap_active = False
                
                else:
                    self.disconnection_counter += 1
                    logger.debug(f"System offline. Counter: {self.disconnection_counter}")
                    
                    if self.disconnection_counter >= self.disconnection_threshold:
                        if not self.ap_active:
                            logger.info("Offline timeout reached. Enabling AP mode.")
                            try:
                                self.manager.start_ap()
                                self.start_flask()
                                self.ap_active = True
                            except Exception as e:
                                logger.error(f"Failed to start AP: {e}")
            
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            time.sleep(self.check_interval)

if __name__ == "__main__":
    monitor = WifiMonitor()
    monitor.run()
