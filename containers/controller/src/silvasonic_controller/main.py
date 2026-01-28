import asyncio
import json
import logging
import logging.handlers
import os
import signal
import sys
import time
import typing
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil
import structlog

# Setup Path to find modules
sys.path.append("/app")  # noqa: E402

from silvasonic_controller.device_manager import DeviceManager  # noqa: E402
from silvasonic_controller.podman_client import PodmanOrchestrator  # noqa: E402
from silvasonic_controller.profiles_loader import (  # noqa: E402
    load_profiles,
)


# Logging
# Logging
def setup_logging() -> None:
    os.makedirs("/var/log/silvasonic", exist_ok=True)

    # Structlog Setup
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Bridge
    pre_chain: list[typing.Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=pre_chain,
    )

    handlers: list[logging.Handler] = []

    # Stdout
    s = logging.StreamHandler(sys.stdout)
    s.setFormatter(formatter)
    handlers.append(s)

    # File
    try:
        f = logging.handlers.TimedRotatingFileHandler(
            "/var/log/silvasonic/controller.log", when="midnight", backupCount=30
        )
        f.setFormatter(formatter)
        handlers.append(f)
    except Exception:
        pass

    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


logger = structlog.get_logger("Main")

STATUS_DIR = "/mnt/data/services/silvasonic/status"


@dataclass
class SessionInfo:
    container_name: str
    rec_id: str
    port: int
    profile_slug: str


class Controller:
    def __init__(self, device_manager: DeviceManager, podman_client: PodmanOrchestrator) -> None:
        self.device_manager = device_manager
        self.orchestrator = podman_client
        self.running = True

        # State: {card_id: SessionInfo}
        self.active_sessions: dict[str, SessionInfo] = {}
        self.unconfigured_devices: list[typing.Any] = []  # List[AudioDevice]

        # Load Profiles
        self.profiles = load_profiles(Path("/app/mic_profiles"))  # Use mounted profiles

    async def adopt_orphans(self) -> None:
        """Adopt existing recorder containers on startup."""
        logger.info("Scanning for existing recorder containers...")
        active = await self.orchestrator.list_active_recorders()

        for container in active:
            try:
                # Parse labels from container info
                # "Labels" key might vary depending on podman version/json format,
                # but with --format json it is usually under "Labels"
                labels = container.get("Labels", {})

                # Check for critical labels
                s_profile = labels.get("silvasonic.profile")
                s_port_str = labels.get("silvasonic.port")
                s_rec_id = labels.get("silvasonic.rec_id")
                s_card_id = labels.get("card_id")

                # Depending on Podman version/format, Names might be a list or string
                c_names = container.get("Names", [])
                c_name = c_names[0] if isinstance(c_names, list) and c_names else str(c_names)

                if s_profile and s_port_str and s_rec_id and s_card_id:
                    port = int(s_port_str)

                    session = SessionInfo(
                        container_name=c_name, rec_id=s_rec_id, port=port, profile_slug=s_profile
                    )

                    self.active_sessions[s_card_id] = session
                    logger.info(f"Adopted existing session: {s_rec_id} (Card {s_card_id})")
                else:
                    logger.warning(
                        f"Found unmanaged/legacy recorder container {c_name} without full labels. "
                        "It will likely be restarted."
                    )
            except Exception as e:
                logger.error(f"Failed to adopt container {container}: {e}")

    async def write_status(self, status: str = "Running") -> None:
        """Writes the Controller's own heartbeat asynchronously."""
        try:
            os.makedirs(STATUS_DIR, exist_ok=True)

            # Simplified metadata for status
            active_list = [s.rec_id for s in self.active_sessions.values()]

            # psutil is fast but blocking. For high frequency, might want to_thread,
            # but for 5s interval it's negligible.
            cpu = psutil.cpu_percent()
            mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            data = {
                "service": "controller",
                "timestamp": time.time(),
                "status": status,
                "cpu_percent": cpu,
                "memory_usage_mb": mem,
                "pid": os.getpid(),
                "meta": {"active_sessions": active_list},
                # Option A: Report unconfigured devices
                "unconfigured_devices": [asdict(d) for d in self.unconfigured_devices],
            }
            status_file = f"{STATUS_DIR}/controller.json"
            tmp_file = f"{status_file}.tmp"

            # File writing
            def _write() -> None:
                with open(tmp_file, "w") as f:
                    json.dump(data, f)
                os.rename(tmp_file, status_file)

            await asyncio.to_thread(_write)

        except Exception as e:
            logger.error(f"Failed to write status: {e}")

    async def write_live_config(self) -> None:
        """Writes the LiveSound configuration (Port Mapping)."""
        try:
            os.makedirs(STATUS_DIR, exist_ok=True)

            # Map: rec_id -> port
            sources = {}
            for s in self.active_sessions.values():
                sources[s.rec_id] = s.port
                # Add Alias for simple slug
                if s.profile_slug not in sources:
                    sources[s.profile_slug] = s.port

            config_file = f"{STATUS_DIR}/livesound_sources.json"
            tmp_file = f"{config_file}.tmp"

            def _write() -> None:
                with open(tmp_file, "w") as f:
                    json.dump(sources, f)
                os.rename(tmp_file, config_file)

            await asyncio.to_thread(_write)
            logger.info(f"Updated live config with {len(sources)} sources")
        except Exception as e:
            logger.error(f"Failed to write live config: {e}")

    async def write_recorder_inventory(self) -> None:
        """Writes detailed recorder inventory for Dashboard (Option C)."""
        try:
            os.makedirs(STATUS_DIR, exist_ok=True)
            inventory = []

            for card_id, session in self.active_sessions.items():
                # Try to find matching profile for name
                profile_name = "Unknown"
                if session.profile_slug:
                    for p in self.profiles:
                        if p.slug == session.profile_slug:
                            profile_name = p.name
                            break

                item = {
                    "rec_id": session.rec_id,
                    "container_name": session.container_name,
                    "status": "Running",  # Inferred
                    "port": session.port,
                    "profile_name": profile_name,
                    "profile_slug": session.profile_slug,
                    "card_id": card_id,
                    # We could match card_id back to device name if we cached scan results,
                    # but session doesn't store device name currently.
                    # For now, this is sufficient.
                }
                inventory.append(item)

            inventory_file = f"{STATUS_DIR}/active_recorders.json"
            tmp_file = f"{inventory_file}.tmp"

            def _write() -> None:
                with open(tmp_file, "w") as f:
                    json.dump(inventory, f, indent=2)
                os.rename(tmp_file, inventory_file)

            await asyncio.to_thread(_write)
        except Exception as e:
            logger.error(f"Failed to write recorder inventory: {e}")

    async def reconcile(self) -> None:
        """Sync Hardware with Containers."""
        devices = await self.device_manager.scan_devices()
        current_card_ids = {d.card_id for d in devices}
        # Reset detected but unconfigured list for this cycle
        self.unconfigured_devices.clear()

        # 1. Cleanup Stale Sessions (Device unplugged)
        active_ids = list(self.active_sessions.keys())
        for card_id in active_ids:
            if card_id not in current_card_ids:
                logger.info(f"Device {card_id} removed. Stopping recorder...")
                session = self.active_sessions[card_id]
                await self.orchestrator.stop_recorder(session.container_name)
                del self.active_sessions[card_id]

        # 2. Spawn New Sessions
        for device in devices:
            if device.card_id in self.active_sessions:
                continue  # Already running

            logger.info(f"New Device Found: {device.name} (Card {device.card_id})")

            # Match Profile
            matched_profile = None
            for p in self.profiles:
                if p.is_mock:
                    continue
                for pattern in p.device_patterns:
                    if pattern.lower() in device.name.lower():
                        matched_profile = p
                        break
                if matched_profile:
                    break

            # Use generic fallback if no match found but device exists
            # (matches logic in profiles_loader but reimplemented here or we rely on logic above?)
            # The profiles_loader logic was: find_matching_profile returns ONE.
            # Here we iterate ALL devices.

            if matched_profile:
                logger.info(f"Matched Profile: {matched_profile.name}")
                rec_id = f"{matched_profile.slug}_{device.card_id}"
                container_name = f"silvasonic_recorder_{rec_id}"

                try:
                    port = 12000 + int(device.card_id)
                except (ValueError, TypeError):
                    port = 12000 + (hash(rec_id) % 100)

                success = await self.orchestrator.spawn_recorder(
                    name=rec_id,
                    profile_slug=matched_profile.slug,
                    device_path=device.dev_path,
                    card_id=device.card_id,
                )

                if success:
                    session = SessionInfo(
                        container_name=container_name,
                        rec_id=rec_id,
                        port=port,
                        profile_slug=matched_profile.slug,
                    )
                    self.active_sessions[device.card_id] = session
                    self.active_sessions[device.card_id] = session
            else:
                logger.warning(f"No profile found for {device.name}, ignoring.")
                self.unconfigured_devices.append(device)

        # Update LiveSound Config
        await self.write_live_config()
        # Option C: Write Active Recorders Inventory
        await self.write_recorder_inventory()

    def _check_profile_updates(self) -> None:
        """Check if profile directory has changed and reload if necessary."""
        try:
            profiles_dir = Path("/app/mic_profiles")
            if not profiles_dir.exists():
                return

            # Simple mtime check on the directory itself (works for added/removed files on Linux ext4)
            # For modified contents of files, we might need to check max mtime of children,
            # but usually directory mtime updates on file add/remove.
            # To be safe for file *edits*, we should check max mtime of all .yml files.
            current_mtime = profiles_dir.stat().st_mtime

            # Also check children to catch file edits
            max_child_mtime = current_mtime
            for p in profiles_dir.glob("*.yml"):
                t = p.stat().st_mtime
                if t > max_child_mtime:
                    max_child_mtime = t

            # Combine logic
            combined_hash = hash((current_mtime, max_child_mtime))

            if not hasattr(self, "_last_profile_hash"):
                self._last_profile_hash = combined_hash
                return

            if combined_hash != self._last_profile_hash:
                logger.info("Detected change in mic_profiles. Reloading...")
                self.profiles = load_profiles(profiles_dir)
                self._last_profile_hash = combined_hash
                # Trigger reconcile to apply new profiles to potentially unconfigured devices
                asyncio.create_task(self.reconcile())

        except Exception as e:
            logger.error(f"Failed to check profile updates: {e}")

    async def monitor_hardware(self) -> None:
        """Background task to poll for hardware changes."""
        monitor = self.device_manager.start_monitoring()
        logger.info("Hardware monitor started.")

        # Initialize hash
        self._check_profile_updates()

        while self.running:
            try:
                # Poll via thread to not block loop
                # This returns pyudev.Device or None
                device = await asyncio.to_thread(monitor.poll, timeout=2.0)
                if device:
                    logger.info(f"Udev Event: {device.action} {device.device_node}")
                    await self.reconcile()
                else:
                    # Timeout, check for profile updates
                    await asyncio.to_thread(self._check_profile_updates)
                    pass
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)

    async def heartbeat_loop(self) -> None:
        """Background task for status writing."""
        while self.running:
            await self.write_status("Running")
            await asyncio.sleep(10)

    async def run(self) -> None:
        logger.info("Starting Silvasonic Controller (AsyncIO)...")

        # Adopt existing containers
        await self.adopt_orphans()

        # Initial Reconcile
        await self.reconcile()

        # Start background tasks
        monitor_task = asyncio.create_task(self.monitor_hardware())
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())

        # Wait until stopped
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            monitor_task.cancel()
            heartbeat_task.cancel()
            logger.info("Shutdown complete.")

    def stop(self) -> None:
        self.running = False


if __name__ == "__main__":
    setup_logging()

    # Run async main
    async def main() -> None:
        controller = Controller(DeviceManager(), PodmanOrchestrator())

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, controller.stop)

        await controller.run()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
