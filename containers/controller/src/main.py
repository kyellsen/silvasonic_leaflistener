
import logging
import sys
import time
import os
import signal
import psutil
import json
from pathlib import Path

# Setup Path to find modules
sys.path.append("/app")

from src.device_manager import DeviceManager, AudioDevice
from src.podman_client import PodmanOrchestrator
from mic_profiles import load_profiles, find_matching_profile, MicrophoneProfile

# Logging
os.makedirs("/var/log/silvasonic", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Controller] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.TimedRotatingFileHandler(
            "/var/log/silvasonic/controller.log", when="midnight", backupCount=30
        )
    ]
)
logger = logging.getLogger("Main")

STATUS_DIR = "/mnt/data/services/silvasonic/status"

class Controller:
    def __init__(self):
        self.device_manager = DeviceManager()
        self.orchestrator = PodmanOrchestrator()
        self.running = True
        
        # State: {card_id: container_id}
        self.active_sessions: dict[str, str] = {} 
        
        # Load Profiles
        self.profiles = load_profiles(Path("/app/mic_profiles")) # Use mounted profiles
        
    def write_status(self, status: str = "Running") -> None:
        """Writes the Controller's own heartbeat."""
        try:
            os.makedirs(STATUS_DIR, exist_ok=True)
            data = {
                "service": "controller",
                "timestamp": time.time(),
                "status": status,
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "pid": os.getpid(),
                "meta": {
                    "active_sessions": list(self.active_sessions.keys())
                }
            }
            status_file = f"{STATUS_DIR}/controller.json"
            tmp_file = f"{status_file}.tmp"
            with open(tmp_file, "w") as f:
                json.dump(data, f)
            os.rename(tmp_file, status_file)
        except Exception as e:
            logger.error(f"Failed to write status: {e}")

    def reconcile(self):
        """Sync Hardware with Containers."""
        devices = self.device_manager.scan_devices()
        current_card_ids = {d.card_id for d in devices}
        
        # 1. Cleanup Stale Sessions (Device unplugged)
        active_ids = list(self.active_sessions.keys())
        for card_id in active_ids:
            if card_id not in current_card_ids:
                logger.info(f"Device {card_id} removed. Stopping recorder...")
                self.orchestrator.stop_recorder(self.active_sessions[card_id])
                del self.active_sessions[card_id]
                
        # 2. Spawn New Sessions
        for device in devices:
            if device.card_id in self.active_sessions:
                continue # Already running
            
            logger.info(f"New Device Found: {device.name} (Card {device.card_id})")
            
            # Match Profile
            
            # Logic to find profile
            matched_profile = None
            for p in self.profiles:
                for pattern in p.device_patterns:
                    if pattern.lower() in device.name.lower():
                        matched_profile = p
                        break
                if matched_profile: break
            
            if not matched_profile:
                # Fallback to Generic
                matched_profile = next((p for p in self.profiles if "generic" in p.slug), None)
            
            if matched_profile:
                logger.info(f"Matched Profile: {matched_profile.name}")
                if self.orchestrator.spawn_recorder(
                    name=f"{matched_profile.slug}_{device.card_id}",
                    profile_slug=matched_profile.slug,
                    device_path=device.dev_path,
                    card_id=device.card_id
                ):
                    self.active_sessions[device.card_id] = f"silvasonic_recorder_{matched_profile.slug}_{device.card_id}"
            else:
                logger.warning(f"No profile found for {device.name}, ignoring.")

    def run(self):
        logger.info("Starting Silvasonic Controller...")
        
        self.reconcile()
        
        monitor = self.device_manager.start_monitoring()
        
        while self.running:
            try:
                self.write_status("Running")
                
                # Poll wait
                device = monitor.poll(timeout=10)
                if device:
                    logger.info(f"Udev Event: {device.action} {device.device_node}")
                    self.reconcile()
                else:
                    self.write_status("Idle")
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(5)

    def stop(self, *args):
        self.running = False

if __name__ == "__main__":
    controller = Controller()
    signal.signal(signal.SIGTERM, controller.stop)
    signal.signal(signal.SIGINT, controller.stop)
    controller.run()
