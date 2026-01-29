import asyncio
import logging
import typing
from dataclasses import dataclass, field

from silvasonic_controller.persistence import DatabaseClient

if typing.TYPE_CHECKING:
    from silvasonic_controller.podman_client import PodmanOrchestrator

logger = logging.getLogger("ServiceManager")


@dataclass
class ServiceConfig:
    image: str
    enabled: bool = False
    restart_policy: str = "always"
    network: str = "silvasonic_default"
    env: dict[str, str] = field(default_factory=dict)
    mounts: list[dict[str, str]] = field(default_factory=list)
    ports: list[str] = field(default_factory=list)


# Hardcoded Registry of Managed Services
# These are the "Apps" the user can toggle.
REGISTRY: dict[str, ServiceConfig] = {
    "birdnet": ServiceConfig(
        image="silvasonic-birdnet:latest",
        enabled=True,  # Default
        env={"PYTHONUNBUFFERED": "1"},
        mounts=[
            {
                "source": "/mnt/data/services/silvasonic/recordings",
                "target": "/data/recordings",
                "mode": "rw",
            },
            {
                "source": "/mnt/data/services/silvasonic/status",
                "target": "/mnt/data/services/silvasonic/status",
                "mode": "rw",
            },
        ],
    ),
    "uploader": ServiceConfig(
        image="silvasonic-uploader:latest",
        enabled=False,
        env={"PYTHONUNBUFFERED": "1"},
        mounts=[
            {
                "source": "/mnt/data/services/silvasonic/recordings",
                "target": "/data/recordings",
                "mode": "rw",
            },
            {"source": "/mnt/data/services/silvasonic/config", "target": "/config", "mode": "ro"},
        ],
    ),
    "weather": ServiceConfig(
        image="silvasonic-weather:latest",
        enabled=True,
        mounts=[
            {"source": "/mnt/data/services/silvasonic/config", "target": "/config", "mode": "ro"},
        ],
    ),
    "livesound": ServiceConfig(
        image="icecast:2.4-alpine",
        enabled=True,
        ports=["8000:8000"],
        mounts=[
            {
                "source": "/mnt/data/services/silvasonic/config/icecast.xml",
                "target": "/etc/icecast.xml",
                "mode": "ro",
            },
        ],
    ),
}


class ServiceManager:
    def __init__(self, orchestrator: "PodmanOrchestrator", db_client: DatabaseClient) -> None:
        self.orchestrator = orchestrator
        self.db = db_client
        self._services: dict[str, ServiceConfig] = REGISTRY.copy()

    async def sync_loop(self) -> None:
        """Background loop to sync enabled/disabled state from DB."""
        logger.info("ServiceManager Sync Loop started.")
        while True:
            try:
                # 1. Fetch Config from DB
                db_config = await self.db.get_service_config()

                # 2. Apply updates
                for name, config in self._services.items():
                    # If DB has an opinion, use it. Otherwise keep default `enabled` from Registry.
                    if name in db_config:
                        should_be_enabled = db_config[name]

                        if should_be_enabled != config.enabled:
                            logger.info(
                                f"Service {name} state changed: {config.enabled} -> {should_be_enabled}"
                            )
                            config.enabled = should_be_enabled

                            if should_be_enabled:
                                await self.start_service(name)
                            else:
                                await self.stop_service(name)

                # 3. Wait
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"ServiceManager Sync Error: {e}")
                await asyncio.sleep(10)

    async def start_service(self, service_name: str) -> bool:
        if service_name not in self._services:
            return False

        config = self._services[service_name]
        # Verify it is enabled before starting (double check)
        if not config.enabled:
            return False

        return await self.orchestrator.spawn_service(
            service_name=service_name,
            image=config.image,
            env_vars=config.env,
            mounts=config.mounts,
            network=config.network,
            restart_policy=config.restart_policy,
            ports=config.ports,
        )

    async def stop_service(self, service_name: str) -> bool:
        container_name = f"silvasonic_{service_name}"
        await self.orchestrator.stop_container(container_name)
        return True
