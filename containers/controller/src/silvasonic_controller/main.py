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
import redis
import structlog
from silvasonic_controller.persistence import DatabaseClient
from silvasonic_controller.service_manager import ServiceManager

# Setup Path to find modules
sys.path.append("/app")

from silvasonic_controller.device_manager import DeviceManager
from silvasonic_controller.podman_client import PodmanOrchestrator
from silvasonic_controller.profiles_loader import load_profiles


def setup_logging() -> None:
    os.makedirs("/var/log/silvasonic", exist_ok=True)

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
    s = logging.StreamHandler(sys.stdout)
    s.setFormatter(formatter)
    handlers.append(s)

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


@dataclass
class SessionInfo:
    container_name: str
    rec_id: str
    port: int
    profile_slug: str
    created_at: float = 0.0
    failure_count: int = 0
    next_retry_timestamp: float = 0.0


class Controller:
    def __init__(self, device_manager: DeviceManager, podman_client: PodmanOrchestrator) -> None:
        self.device_manager = device_manager
        self.orchestrator = podman_client
        self.running = True

        self.active_sessions: dict[str, SessionInfo] = {}
        self.unconfigured_devices: list[typing.Any] = []

        self.profiles = load_profiles(Path("/app/mic_profiles"))

        # Database Configuration Client
        self.db = DatabaseClient()

        # Service Manager (Uses DB now)
        self.service_manager = ServiceManager(self.orchestrator, self.db)

        # Redis Connection
        self.redis = redis.Redis(
            host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=2.0
        )

    async def adopt_orphans(self) -> None:
        logger.info("Scanning for existing recorder containers...")
        active = await self.orchestrator.list_active_recorders()

        for container in active:
            try:
                labels = container.get("Labels", {})
                s_profile = labels.get("silvasonic.profile")
                s_port_str = labels.get("silvasonic.port")
                s_rec_id = labels.get("silvasonic.rec_id")
                s_card_id = labels.get("card_id")

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
                    logger.warning(f"Found unmanaged recorder {c_name}. Ignoring.")
            except Exception as e:
                logger.error(f"Failed to adopt container {container}: {e}")

    async def write_status(self) -> None:
        """Writes Heartbeat to Redis."""
        try:
            active_list = [s.rec_id for s in self.active_sessions.values()]
            cpu = psutil.cpu_percent()
            mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            data = {
                "service": "controller",
                "timestamp": time.time(),
                "status": "Running",
                "cpu_percent": cpu,
                "memory_usage_mb": mem,
                "pid": os.getpid(),
                "meta": {"active_sessions": active_list},
                "unconfigured_devices": [asdict(d) for d in self.unconfigured_devices],
            }

            # Write to Redis with TTL 15s
            await asyncio.to_thread(self.redis.set, "status:controller", json.dumps(data), ex=15)

        except Exception as e:
            logger.error(f"Failed to write status to Redis: {e}")

    async def reconcile(self) -> None:
        """Sync Hardware with Containers."""
        devices = await self.device_manager.scan_devices()
        current_card_ids = {d.card_id for d in devices}
        self.unconfigured_devices.clear()

        # 1. Cleanup Stale
        active_ids = list(self.active_sessions.keys())
        for card_id in active_ids:
            if card_id not in current_card_ids:
                logger.info(f"Device {card_id} removed. Stopping recorder...")
                session = self.active_sessions[card_id]
                await self.orchestrator.stop_recorder(session.container_name)
                del self.active_sessions[card_id]

        # 2. Spawn New
        for device in devices:
            if device.card_id in self.active_sessions:
                continue

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

            if matched_profile:
                logger.info(f"Matched Profile: {matched_profile.name}")
                rec_id = f"{matched_profile.slug}_{device.card_id}"
                container_name = f"silvasonic_recorder_{rec_id}"
                port = 12000 + int(device.card_id)  # Simple int parse for local cards

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
            else:
                logger.warning(f"No profile found for {device.name}")
                self.unconfigured_devices.append(device)

    async def monitor_hardware(self) -> None:
        monitor = self.device_manager.start_monitoring()
        logger.info("Hardware monitor started.")
        while self.running:
            try:
                device = await asyncio.to_thread(monitor.poll, timeout=2.0)
                if device:
                    logger.info(f"Udev Event: {device.action} {device.device_node}")
                    await self.reconcile()
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)

    async def heartbeat_loop(self) -> None:
        while self.running:
            await self.write_status()
            await asyncio.sleep(5)

    async def run(self) -> None:
        logger.info("Starting Silvasonic Controller V2...")

        await self.adopt_orphans()
        await self.reconcile()

        # Start Service Manager Sync Loop
        service_task = asyncio.create_task(self.service_manager.sync_loop())

        monitor_task = asyncio.create_task(self.monitor_hardware())
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())

        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            monitor_task.cancel()
            heartbeat_task.cancel()
            service_task.cancel()
            logger.info("Shutdown complete.")

    def stop(self) -> None:
        self.running = False


if __name__ == "__main__":
    setup_logging()

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
