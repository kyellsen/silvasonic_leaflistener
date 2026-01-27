
import logging
import logging.handlers
import sys
import time
import os
import signal
import psutil
import json
from pathlib import Path
from dataclasses import dataclass

# Setup Path to find modules
sys.path.append("/app")

from src.device_manager import DeviceManager, AudioDevice
from src.podman_client import PodmanOrchestrator
from src.profiles_loader import load_profiles, find_matching_profile, MicrophoneProfile

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

@dataclass
class SessionInfo:
    container_name: str
    rec_id: str
    port: int
    profile_slug: str

class Controller:
    def __init__(self):
        self.device_manager = DeviceManager()
        self.orchestrator = PodmanOrchestrator()
        self.running = True
        
        # State: {card_id: SessionInfo}
        self.active_sessions: dict[str, SessionInfo] = {} 
        
        # Load Profiles
        self.profiles = load_profiles(Path("/app/mic_profiles")) # Use mounted profiles
        
    def write_status(self, status: str = "Running") -> None:
        """Writes the Controller's own heartbeat."""
        try:
            os.makedirs(STATUS_DIR, exist_ok=True)
            
            # Simplified metadata for status
            active_list = [s.rec_id for s in self.active_sessions.values()]
            
            data = {
                "service": "controller",
                "timestamp": time.time(),
                "status": status,
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "pid": os.getpid(),
                "meta": {
                    "active_sessions": active_list
                }
            }
            status_file = f"{STATUS_DIR}/controller.json"
            tmp_file = f"{status_file}.tmp"
            with open(tmp_file, "w") as f:
                json.dump(data, f)
            os.rename(tmp_file, status_file)
        except Exception as e:
            logger.error(f"Failed to write status: {e}")

    def write_live_config(self) -> None:
        """Writes the LiveSound configuration (Port Mapping)."""
        try:
            os.makedirs(STATUS_DIR, exist_ok=True)
            
            # Map: rec_id -> port
            # e.g. {"front_mic_1": 12001, "back_mic_2": 12002}
            sources = {}
            for s in self.active_sessions.values():
                sources[s.rec_id] = s.port
                # Add Alias for simple slug (e.g. 'rode_nt' -> 12001) for frontend convenience
                if s.profile_slug not in sources:
                     sources[s.profile_slug] = s.port
            
            config_file = f"{STATUS_DIR}/livesound_sources.json"
            tmp_file = f"{config_file}.tmp"
            with open(tmp_file, "w") as f:
                json.dump(sources, f)
            os.rename(tmp_file, config_file)
            logger.info(f"Updated live config with {len(sources)} sources")
        except Exception as e:
            logger.error(f"Failed to write live config: {e}")

    def reconcile(self):
        """Sync Hardware with Containers."""
        devices = self.device_manager.scan_devices()
        current_card_ids = {d.card_id for d in devices}
        
        # 1. Cleanup Stale Sessions (Device unplugged)
        active_ids = list(self.active_sessions.keys())
        for card_id in active_ids:
            if card_id not in current_card_ids:
                logger.info(f"Device {card_id} removed. Stopping recorder...")
                session = self.active_sessions[card_id]
                self.orchestrator.stop_recorder(session.container_name)
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
            
            if matched_profile:
                logger.info(f"Matched Profile: {matched_profile.name}")
                
                # Deterministic IDs and Ports
                rec_id = f"{matched_profile.slug}_{device.card_id}"
                container_name = f"silvasonic_recorder_{rec_id}"
                
                # Port Calculation (Matching podman_client logic, or we rely on podman_client to respect passed env?)
                # Controller decides the port now implicitly by knowing the card_id
                try:
                    port = 12000 + int(device.card_id)
                except:
                    # Fallback for non-numeric card IDs? (Rare in ALSA)
                    port = 12000 + (hash(rec_id) % 100)

                if self.orchestrator.spawn_recorder(
                    name=rec_id, # podman_client expects unique component for name
                    profile_slug=matched_profile.slug,
                    device_path=device.dev_path,
                    card_id=device.card_id
                ):
                    session = SessionInfo(
                        container_name=container_name,
                        rec_id=rec_id,
                        port=port,
                        profile_slug=matched_profile.slug
                    )
                    self.active_sessions[device.card_id] = session
            else:
                logger.warning(f"No profile found for {device.name}, ignoring.")

        # Update LiveSound Config
        self.write_live_config()

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
