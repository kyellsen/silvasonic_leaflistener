import json
import logging
import os
import subprocess
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class RcloneWrapper:
    """A robust wrapper around the rclone CLI."""

    def __init__(self, config_path: str = "/config/rclone/rclone.conf"):
        self.config_path = config_path
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    def configure_webdav(self, remote_name: str, url: str, user: str, password: str) -> None:
        """Configures a remote using 'rclone config create'."""
        logger.info(f"Configuring remote '{remote_name}' for WebDAV...")

        # Mask password in logs
        cmd = [
            "rclone",
            "config",
            "create",
            remote_name,
            "webdav",
            f"url={url}",
            "vendor=nextcloud",
            f"user={user}",
            f"pass={password}",
            "--obscure",  # Obscure the password
            "--non-interactive",  # Don't prompt
            "--config",
            self.config_path,
        ]

        try:
            # We don't log the command here to avoid leaking secrets if debug is on
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Remote '{remote_name}' configured successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to configure remote: {e.stderr}")
            raise

    def sync(
        self,
        source: str,
        dest: str,
        transfers: int = 4,
        checkers: int = 8,
        callback: Callable[[str, str, str], None] | None = None,
    ) -> bool:
        """Runs the sync command and streams output.

        Returns True if successful, False otherwise.
        """
        cmd = [
            "rclone",
            "sync",
            source,
            dest,
            "--transfers",
            str(transfers),
            "--checkers",
            str(checkers),
            "--verbose",
            "--config",
            self.config_path,
            "--disable-http2",
            "--retries",
            "5",
        ]

        return self._run_transfer(cmd, source, dest, callback=callback)

    def copy(
        self,
        source: str,
        dest: str,
        transfers: int = 4,
        checkers: int = 8,
        min_age: str | None = None,
        callback: Callable[[str, str, str], None] | None = None,
    ) -> bool:
        """Runs the copy command (additive only) and streams output.

        Returns True if successful, False otherwise.
        """
        cmd = [
            "rclone",
            "copy",
            source,
            dest,
            "--transfers",
            str(transfers),
            "--checkers",
            str(checkers),
            "--verbose",
            "--config",
            self.config_path,
            "--disable-http2",
            "--retries",
            "5",
        ]

        if min_age:
            cmd.extend(["--min-age", min_age])

        return self._run_transfer(cmd, source, dest, callback=callback)

    def _run_transfer(
        self,
        cmd: list[str],
        source: str,
        dest: str,
        callback: Callable[[str, str, str], None] | None = None,
    ) -> bool:
        """Helper to run transfer commands and stream logs. Returns True on success."""
        logger.info(f"Starting transfer: {source} -> {dest}")
        start_time = time.time()

        # Regex for parsing rclone logs
        import re

        # INFO : file.txt: Copied (new)
        re_success = re.compile(r"INFO\s+:\s+(.+?):\s+Copied")
        # ERROR : file.txt: Failed to copy: error message
        re_error = re.compile(r"ERROR\s+:\s+(.+?):\s+Failed to copy:\s+(.*)")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stdout and stderr
                text=True,
                bufsize=1,
            )

            output_buffer = []

            if process.stdout:
                # Stream logs line by line
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        logger.debug(f"[Rclone] {line}")
                        output_buffer.append(line)
                        # Keep buffer size manageable (e.g., last 100 lines)
                        if len(output_buffer) > 100:
                            output_buffer.pop(0)

                        # Callback parsing
                        if callback:
                            try:
                                # Check Success
                                m_ok = re_success.search(line)
                                if m_ok:
                                    filename = m_ok.group(1).strip()
                                    callback(filename, "success", "")
                                    continue

                                # Check Error
                                m_err = re_error.search(line)
                                if m_err:
                                    filename = m_err.group(1).strip()
                                    err_msg = m_err.group(2).strip()
                                    callback(filename, "failed", err_msg)
                            except Exception as e:
                                logger.error(f"Callback error analyzing line '{line}': {e}")

            process.wait()

            duration = time.time() - start_time
            if process.returncode == 0:
                logger.info(f"Transfer completed successfully in {duration:.2f}s")
                return True
            else:
                logger.error(f"Transfer failed with return code {process.returncode}")
                # logger.error("--- Rclone Output Dump (Last 100 lines) ---")
                # for line in output_buffer:
                #    logger.error(f"[Rclone] {line}")
                # logger.error("-------------------------------------------")
                return False

        except Exception as e:
            logger.error(f"Transfer execution error: {e}")
            return False

    def list_files(self, remote: str) -> dict[str, int] | None:
        """Lists files on the remote and returns a dict {filename: size}.

        Returns None if listing fails.
        Uses 'rclone lsjson' for parsing.
        """
        cmd = ["rclone", "lsjson", remote, "--recursive", "--config", self.config_path]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            items = json.loads(result.stdout)

            # Create a simple dict: relative_path -> size
            # rclone lsjson returns 'Path' relative to the root of the remote
            return {item["Path"]: item["Size"] for item in items if not item["IsDir"]}

        except Exception as e:
            logger.error(f"Failed to list remote files: {e}")
            return None

    def get_disk_usage_percent(self, path: str) -> float:
        """Checks disk usage percentage for the given path."""
        try:
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            percent = (used / total) * 100
            return percent
        except Exception as e:
            logger.error(f"Failed to check disk usage: {e}")
            return 0.0
