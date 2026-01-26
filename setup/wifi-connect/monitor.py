import logging
import os
import signal
import subprocess
import time

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
        self.current_process = None
        self.mode = "none" # none, setup, redirect
        self.check_interval = 10
        self.disconnection_counter = 0
        self.disconnection_threshold = 3

    def start_service(self, service_name):
        """Start a web service (app.py or redirect.py)"""
        script_map = {
            "setup": "app.py",
            "redirect": "redirect.py"
        }

        if service_name not in script_map:
            return

        # Stop existing if different
        if self.mode != service_name:
            self.stop_service()

        if self.current_process is None:
            logger.info(f"Starting {service_name} service...")
            env = os.environ.copy()
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_map[service_name])

            try:
                self.current_process = subprocess.Popen(
                    ["python3", script_path],
                    env=env,
                    preexec_fn=os.setsid
                )
                self.mode = service_name
            except Exception as e:
                logger.error(f"Failed to start {service_name}: {e}")

    def stop_service(self):
        if self.current_process:
            logger.info(f"Stopping {self.mode} service...")
            try:
                os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                self.current_process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error killing process: {e}")
            self.current_process = None
            self.mode = "none"

    def run(self):
        logger.info("WiFi Monitor Service Started")
        time.sleep(15)

        while True:
            try:
                connected = self.manager.is_connected()

                if connected:
                    # SYSTEM ONLINE
                    self.disconnection_counter = 0

                    # Ensure AP is off
                    if self.manager.is_ap_running():
                        logger.info("Connection detected! Stopping AP.")
                        self.manager.stop_ap()

                    # Ensure Redirector is running
                    if self.mode != "redirect":
                        self.start_service("redirect")

                else:
                    # SYSTEM OFFLINE
                    self.disconnection_counter += 1
                    logger.debug(f"System offline. Counter: {self.disconnection_counter}")

                    if self.disconnection_counter >= self.disconnection_threshold:
                        # Ensure AP is on
                        if not self.manager.is_ap_running():
                            logger.info("Offline timeout. Starting AP.")
                            self.manager.start_ap()

                        # Ensure Setup App is running
                        if self.mode != "setup":
                            self.start_service("setup")

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            time.sleep(self.check_interval)

if __name__ == "__main__":
    monitor = WifiMonitor()
    monitor.run()
