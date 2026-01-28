import logging
import os
import typing
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

if typing.TYPE_CHECKING:
    from silvasonic_controller.podman_client import PodmanOrchestrator

logger = logging.getLogger("ServiceManager")


class ServiceMount(BaseModel):
    source: str
    target: str
    mode: str = "z"


class ServiceDefinition(BaseModel):
    image: str
    enabled: bool = True
    restart_policy: str = "always"
    network: str = "silvasonic_default"
    env: dict[str, str] = Field(default_factory=dict)
    mounts: list[ServiceMount] = Field(default_factory=list)
    ports: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class ServiceConfigRoot(BaseModel):
    services: dict[str, ServiceDefinition]


class ServiceManager:
    def __init__(
        self, orchestrator: "PodmanOrchestrator", config_path: str | Path | None = None
    ) -> None:
        self.orchestrator = orchestrator
        self._services: dict[str, ServiceDefinition] = {}

        # Default config path logic
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Fallback to standard location
            data_dir = os.environ.get("SILVASONIC_DATA_DIR", "/mnt/data/services/silvasonic")
            self.config_path = Path(data_dir) / "config" / "dynamic_services.yaml"

        self._load_initial_registry()

    def _load_initial_registry(self) -> None:
        """
        Load services from the YAML configuration file.
        """
        if not self.config_path.exists():
            logger.warning(
                f"Config file not found at {self.config_path}. No dynamic services loaded."
            )
            return

        try:
            with open(self.config_path) as f:
                raw_config = yaml.safe_load(f)

            if not raw_config:
                logger.warning(f"Config file at {self.config_path} is empty.")
                return

            # Validate and parse using Pydantic
            config_root = ServiceConfigRoot(**raw_config)
            self._services = config_root.services
            logger.info(f"Loaded {len(self._services)} services from {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to load service registry from {self.config_path}: {e}")

    def _resolve_env_vars(self, env_vars: dict[str, str]) -> dict[str, str]:
        """
        Optional: Resolve simple env var placeholders if needed.
        Currently relying on Podman/Compose to handle env expansion or pre-processing.
        But for now, just return as is.
        """
        return env_vars

    async def sync_services(self) -> None:
        """
        Reconcile expected services with running containers.
        """
        # TODO: Implement full reconciliation loop
        pass

    async def start_service(self, service_name: str) -> bool:
        if service_name not in self._services:
            logger.error(f"Service {service_name} not found in registry.")
            return False

        config = self._services[service_name]
        if not config.enabled:
            logger.info(f"Service {service_name} is disabled. Skipping.")
            return False

        logger.info(f"Starting service: {service_name}")

        # Convert Pydantic models to dicts for the orchestrator
        mounts_list = [m.model_dump() for m in config.mounts]

        return bool(
            await self.orchestrator.spawn_service(
                service_name=service_name,
                image=config.image,
                env_vars=config.env,
                mounts=mounts_list,
                network=config.network,
                restart_policy=config.restart_policy,
                ports=config.ports,
            )
        )

    async def stop_service(self, service_name: str) -> bool:
        logger.info(f"Stopping service: {service_name}")
        # Assuming container name convention silvasonic_{service_name}
        container_name = f"silvasonic_{service_name}"
        await self.orchestrator.stop_container(container_name)
        return True
