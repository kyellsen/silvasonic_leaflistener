import asyncio
import json
import logging
import os
import typing

logger = logging.getLogger("PodmanClient")


class PodmanOrchestrator:
    def __init__(self, socket_path: str = "/run/user/1000/podman/podman.sock") -> None:
        # We assume we are inside the 'controller' container,
        # which has the host socket mounted.
        pass

    async def list_active_recorders(self) -> list[dict[typing.Any, typing.Any]]:
        """Returns list of running recorder containers."""
        cmd = [
            "podman",
            "ps",
            "--format",
            "json",
            "--filter",
            "label=managed_by=silvasonic-controller",
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0 and stdout:
                output = stdout.decode().strip()
                if output:
                    try:
                        return typing.cast(list[dict[typing.Any, typing.Any]], json.loads(output))
                    except json.JSONDecodeError:
                        # Fallback if podman returns concatenated objects (rare with --format json array)
                        return []
            return []
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    async def spawn_recorder(
        self, name: str, profile_slug: str, device_path: str, card_id: str
    ) -> bool:
        """Spawn a new recorder container asynchronously."""

        container_name = f"silvasonic_recorder_{name}"

        # Determine unique stream port
        try:
            port_offset = int(card_id)
        except (ValueError, TypeError):
            port_offset = hash(name) % 100

        stream_port = 12000 + port_offset  # e.g. 12001

        rec_id = f"{profile_slug}_{card_id}"

        # ENVIRONMENT mapping
        env_vars = [
            "-e",
            "PYTHONUNBUFFERED=1",
            "-e",
            f"AUDIO_PROFILE={profile_slug}",
            "-e",
            f"RECORDER_ID={rec_id}",
            "-e",
            f"LIVE_STREAM_PORT={stream_port}",
            "-e",
            "LIVE_STREAM_TARGET=silvasonic_livesound",
            "-e",
            "SILVASONIC_DATA_DIR=/mnt/data/services/silvasonic",
        ]

        host_data_dir = os.environ.get("HOST_SILVASONIC_DATA_DIR", "/mnt/data/services/silvasonic")

        volumes = [
            "-v",
            f"/dev/snd/pcmC{card_id}D0c:/dev/snd/pcmC{card_id}D0c",
            "--device",
            f"/dev/snd/controlC{card_id}",
            "--device",
            f"/dev/snd/pcmC{card_id}D0c",
            "-v",
            "/proc/asound:/proc/asound:ro",
            "-v",
            "/sys:/sys:ro",
            "-v",
            f"{host_data_dir}/recorder/recordings:/data/recording:z",
            "-v",
            f"{host_data_dir}/logs:/var/log/silvasonic:z",
            "-v",
            f"{host_data_dir}/status:/mnt/data/services/silvasonic/status:z",
        ]

        # For Dev Source Mounting
        host_src = os.environ.get("HOST_RECORDER_SRC")
        if host_src:
            volumes.extend(["-v", f"{host_src}:/app/src:z"])

        cmd = [
            "podman",
            "run",
            "-d",
            "--name",
            container_name,
            "--replace",
            "--label",
            "managed_by=silvasonic-controller",
            "--label",
            f"card_id={card_id}",
            "--label",
            f"silvasonic.profile={profile_slug}",
            "--label",
            f"silvasonic.port={stream_port}",
            "--label",
            f"silvasonic.rec_id={rec_id}",
            "--privileged",
            "--network",
            "silvasonic_default",
            *env_vars,
            *volumes,
            "silvasonic-recorder:latest",
        ]

        logger.info(f"Spawning {container_name} on port {stream_port}...")
        logger.debug(f"CMD: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                err_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Failed to spawn: {err_msg}")
                return False
            return True
        except Exception as e:
            logger.error(f"Spawn Exception: {e}")
            return False

    async def spawn_service(
        self,
        service_name: str,
        image: str,
        env_vars: dict[str, str],
        mounts: list[dict[str, str]],
        network: str = "silvasonic_default",
        restart_policy: str = "always",
        ports: list[str] | None = None,
        labels: dict[str, str] | None = None,
    ) -> bool:
        """Spawn a generic service container."""
        container_name = f"silvasonic_{service_name}"

        # Prepare Env Vars
        env_args = []
        for k, v in env_vars.items():
            env_args.extend(["-e", f"{k}={v}"])

        # Prepare Mounts
        vol_args = []
        for mount in mounts:
            # mount dict: {source, target, mode}
            mode = f":{mount.get('mode', 'z')}" if mount.get("mode") else ""
            vol_args.extend(["-v", f"{mount['source']}:{mount['target']}{mode}"])

        # Prepare Ports
        port_args = []
        if ports:
            for p in ports:
                port_args.extend(["-p", p])

        # Default Labels
        if labels is None:
            labels = {}
        labels["managed_by"] = "silvasonic-controller"
        labels["silvasonic.service"] = service_name

        label_args = []
        for k, v in labels.items():
            label_args.extend(["--label", f"{k}={v}"])

        cmd = [
            "podman",
            "run",
            "-d",
            "--name",
            container_name,
            "--replace",
            f"--restart={restart_policy}",
            "--network",
            network,
            *env_args,
            *vol_args,
            *port_args,
            *label_args,
            image,
        ]

        logger.info(f"Spawning service {container_name}...")
        logger.debug(f"CMD: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                err_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Failed to spawn {service_name}: {err_msg}")
                return False
            return True
        except Exception as e:
            logger.error(f"Spawn Exception for {service_name}: {e}")
            return False

    async def stop_container(self, container_name: str) -> None:
        """Stop and remove a generic container."""
        try:
            # Stop
            p_stop = await asyncio.create_subprocess_exec(
                "podman",
                "stop",
                container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await p_stop.wait()

            # Remove
            p_rm = await asyncio.create_subprocess_exec(
                "podman",
                "rm",
                "-f",
                container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await p_rm.wait()
        except Exception as e:
            logger.error(f"Error stopping container {container_name}: {e}")

    async def stop_recorder(self, container_id: str) -> None:
        """Stop a recorder container asynchronously."""
        # Wrapper around generic stop for backward compatibility
        await self.stop_container(container_id)
