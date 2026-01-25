import subprocess
import logging
import time
import os
from typing import Optional

logger = logging.getLogger(__name__)

class RcloneWrapper:
    """
    A robust wrapper around the rclone CLI.
    """

    def __init__(self, config_path: str = "/config/rclone/rclone.conf"):
        self.config_path = config_path
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    def configure_webdav(self, remote_name: str, url: str, user: str, password: str):
        """
        Configures a remote using 'rclone config create'.
        """
        logger.info(f"Configuring remote '{remote_name}' for WebDAV...")
        
        # Mask password in logs
        cmd = [
            "rclone", "config", "create", remote_name, "webdav",
            f"url={url}",
            "vendor=nextcloud",
            f"user={user}",
            f"pass={password}",
            "--obscure",          # Obscure the password
            "--non-interactive",  # Don't prompt
            "--config", self.config_path
        ]
        
        try:
            # We don't log the command here to avoid leaking secrets if debug is on
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Remote '{remote_name}' configured successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to configure remote: {e.stderr}")
            raise

    def sync(self, source: str, dest: str, transfers: int = 4, checkers: int = 8):
        """
        Runs the sync command and streams output.
        """
        cmd = [
            "rclone", "sync", source, dest,
            "--transfers", str(transfers),
            "--checkers", str(checkers),
            "--verbose",
            "--config", self.config_path
        ]
        
        logger.info(f"Starting sync: {source} -> {dest}")
        start_time = time.time()
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream logs line by line
            for line in process.stdout:
                line = line.strip()
                if line:
                    logger.debug(f"[Rclone] {line}")
            
            process.wait()
            
            duration = time.time() - start_time
            if process.returncode == 0:
                logger.info(f"Sync completed successfully in {duration:.2f}s")
            else:
                logger.error(f"Sync failed with return code {process.returncode}")
                # We don't raise here, we let the main loop handle (retry)
                
        except Exception as e:
            logger.error(f"Sync execution error: {e}")
