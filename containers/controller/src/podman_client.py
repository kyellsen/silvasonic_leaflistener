
import logging
import subprocess
import os
import json
import time

logger = logging.getLogger("PodmanClient")

class PodmanOrchestrator:
    def __init__(self):
        # We assume we are inside the 'controller' container,
        # which has the host socket mounted.
        pass

    def list_active_recorders(self) -> list[dict]:
        """Returns list of running recorder containers."""
        cmd = [
            "podman", "ps", "--format", "json",
            "--filter", "label=managed_by=silvasonic-controller"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                # Handle potentially multiple JSON objects or a list?
                # podman ps json usually returns a list [{},{}]
                try:
                    return json.loads(res.stdout)
                except json.JSONDecodeError:
                    # Sometimes podman < 3 outputs concatenated objects?
                    # But usually list.
                   return []
            return []
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    def spawn_recorder(self, name: str, profile_slug: str, device_path: str, card_id: str) -> bool:
        """Spawn a new recorder container."""
        
        container_name = f"silvasonic_recorder_{name}"
        
        # Determine unique stream port (simple hash-based or managed allocation?)
        # Let's use a base port + card_id (if numeric) to be deterministic?
        try:
            port_offset = int(card_id)
        except:
            port_offset = hash(name) % 100
            
        stream_port = 12000 + port_offset # e.g. 12001
        
        # We need to run the container in the SAME network as the others
        # Usually they are in a bridged network created by compose.
        # Check hostname logic.
        
        rec_id = f"{profile_slug}_{card_id}"
        
        # ENVIRONMENT mapping
        env_vars = [
            "-e", "PYTHONUNBUFFERED=1",
            "-e", f"AUDIO_PROFILE={profile_slug}",
            "-e", f"RECORDER_ID={rec_id}",
            "-e", f"LIVE_STREAM_PORT={stream_port}",
            "-e", "LIVE_STREAM_TARGET=silvasonic_livesound", # DNS name in compose network
            "-e", "SILVASONIC_DATA_DIR=/mnt/data/services/silvasonic" # Internal path logic?
        ]
        
        # VOLUME mapping
        # We need to map the HOST paths into the NEW container.
        # But we are INSIDE a container. We only know the internal paths?
        # NO! We must know the HOST paths because we are telling the HOST daemon what to do.
        # Issue: The controller needs to know the HOST path of the data dir.
        # Solution: Pass HOST_DATA_DIR env var to controller.
        
        host_data_dir = os.environ.get("HOST_SILVASONIC_DATA_DIR", "/mnt/data/services/silvasonic")
        
        volumes = [
            "-v", f"/dev/snd/pcmC{card_id}D0c:/dev/snd/pcmC{card_id}D0c", # Specific device?
            # Actually, just map the specific device needed
            "--device", f"/dev/snd/controlC{card_id}", # Control device needed for ALSA lib
            "--device", f"/dev/snd/pcmC{card_id}D0c",
            
            # Application Binding
            # Ideally we use the image 'silvasonic-recorder:latest' 
            # We don't mount source code in prod dynamic spawning usually, 
            # but for consistency with previous compose:
            # We can't easily map "./containers/recorder/src" relative path from here 
            # unless we know where we are on host.
            # Simplified: Assume Image is built and self-contained OR
            # Require HOST_PROJECT_DIR for dev mounts.
            
            # Data mounts
            "-v", f"{host_data_dir}/recorder/recordings:/data/recording:z",
            "-v", f"{host_data_dir}/logs:/var/log/silvasonic:z",
            "-v", f"{host_data_dir}/status:/mnt/data/services/silvasonic/status:z"
        ]
        
        # For Dev Source Mounting (Optional/Tricky)
        # If HOST_SOURCE_DIR is set, mount it.
        host_src = os.environ.get("HOST_RECORDER_SRC")
        if host_src:
             volumes.extend(["-v", f"{host_src}:/app/src:z"])

        cmd = [
            "podman", "run", "-d",
            "--name", container_name,
            "--replace", # Replace if exists (stale)
            "--label", "managed_by=silvasonic-controller",
            "--label", f"card_id={card_id}",
            "--privileged", # Required for full hardware access (Root-based architecture)
            # Networking
            "--network", "silvasonic_default", # Assuming compose project name 'silvasonic'
            *env_vars,
            *volumes,
            "silvasonic-recorder:latest"
        ]
        
        logger.info(f"Spawning {container_name} on port {stream_port}...")
        logger.debug(f"CMD: {' '.join(cmd)}")
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"Failed to spawn: {res.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Spawn Exception: {e}")
            return False

    def stop_recorder(self, container_id: str):
        subprocess.run(["podman", "stop", container_id], capture_output=True)
        # We rely on --rm? No, we used --replace.
        # But explicit cleanup is good.
        subprocess.run(["podman", "rm", "-f", container_id], capture_output=True)
