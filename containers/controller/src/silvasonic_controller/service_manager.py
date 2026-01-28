import logging
import os
import typing
from dataclasses import dataclass

if typing.TYPE_CHECKING:
    from silvasonic_controller.podman_client import PodmanOrchestrator

logger = logging.getLogger("ServiceManager")


@dataclass
class ServiceConfig:
    name: str
    image: str
    enabled: bool
    env: dict[str, str]
    mounts: list[dict[str, str]]  # source, target, mode
    restart_policy: str = "always"
    ports: list[str] | None = None
    network: str = "silvasonic_default"


class ServiceManager:
    def __init__(
        self, orchestrator: "PodmanOrchestrator", db_connection_string: str | None = None
    ) -> None:
        self.orchestrator = orchestrator
        # TODO: Initialize DB connection here or injected
        # For now, we simulate a DB/Registry with the seed values
        self._services: dict[str, ServiceConfig] = {}
        self._load_initial_registry()

    def _load_initial_registry(self) -> None:
        """
        Mock registry loader. In real impl this would query DB.
        """
        # Resolving Host Path using same logic as Controller
        host_data_dir = os.environ.get("HOST_SILVASONIC_DATA_DIR", "/mnt/data/services/silvasonic")

        self._services["birdnet"] = ServiceConfig(
            name="birdnet",
            image="silvasonic-birdnet:latest",
            enabled=True,
            env={
                "PYTHONUNBUFFERED": "1",
                "INPUT_DIR": "/data/recording",
                "RESULTS_DIR": "/data/results",
                "MIN_CONFIDENCE": "0.7",
                "RECURSIVE_WATCH": "true",
            },
            mounts=[
                {
                    "source": f"{host_data_dir}/recorder/recordings",
                    "target": "/data/recording",
                    "mode": "ro",
                },
                {"source": f"{host_data_dir}/config", "target": "/config", "mode": "ro"},
                {
                    "source": f"{host_data_dir}/birdnet/results",
                    "target": "/data/results",
                    "mode": "z",
                },
                {"source": f"{host_data_dir}/logs", "target": "/var/log/silvasonic", "mode": "z"},
                {
                    "source": f"{host_data_dir}/status",
                    "target": "/mnt/data/services/silvasonic/status",
                    "mode": "z",
                },
                {
                    "source": f"{host_data_dir}/notifications",
                    "target": "/data/notifications",
                    "mode": "z",
                },
            ],
        )

        self._services["weather"] = ServiceConfig(
            name="weather",
            image="silvasonic-weather:latest",
            enabled=True,
            env={},
            mounts=[
                {"source": f"{host_data_dir}/config", "target": "/config", "mode": "z"},
                {"source": f"{host_data_dir}/logs", "target": "/var/log/silvasonic", "mode": "z"},
            ],
        )

    async def sync_services(self) -> None:
        """
        Reconcile expected services with running containers.
        """
        # 1. Get running generic services (filter by managed_by=silvasonic-controller-service)
        pass  # Implementation in main loop usually, but here we can manage it.

    async def start_service(self, service_name: str) -> bool:
        if service_name not in self._services:
            logger.error(f"Service {service_name} not found in registry.")
            return False

        config = self._services[service_name]
        logger.info(f"Starting service: {service_name}")

        return await self.orchestrator.spawn_service(
            service_name=config.name,
            image=config.image,
            env_vars=config.env,
            mounts=config.mounts,
            network=config.network,
        )

    async def stop_service(self, service_name: str) -> bool:
        logger.info(f"Stopping service: {service_name}")
        # Assuming container name convention silvasonic_{service_name}
        container_name = f"silvasonic_{service_name}"
        await self.orchestrator.stop_container(container_name)
        return True
