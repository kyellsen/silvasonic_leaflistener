import asyncio
import json
import logging
import os
import re
import typing
from collections.abc import Callable

logger = logging.getLogger(__name__)


class RcloneWrapper:
    """A robust wrapper around the rclone CLI using AsyncIO."""

    def __init__(self, config_path: str = "/config/rclone/rclone.conf"):
        self.config_path = config_path
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    async def configure_webdav(self, remote_name: str, url: str, user: str, password: str) -> None:
        """Configures a remote using 'rclone config create'."""
        logger.info(f"Configuring remote '{remote_name}' for WebDAV...")

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
            # Run in subprocess
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                logger.info(f"Remote '{remote_name}' configured successfully.")
            else:
                logger.error(f"Failed to configure remote: {stderr.decode()}")
                raise Exception(f"Rclone config failed: {stderr.decode()}")

        except Exception as e:
            logger.error(f"Failed to configure remote: {e}")
            raise

    async def sync(
        self,
        source: str,
        dest: str,
        transfers: int = 4,
        checkers: int = 8,
        callback: Callable[[str, str, str], typing.Awaitable[None]] | None = None,
    ) -> bool:
        """Runs the sync command asynchronously."""
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
        return await self._run_transfer(cmd, source, dest, callback=callback)

    async def copy(
        self,
        source: str,
        dest: str,
        transfers: int = 4,
        checkers: int = 8,
        min_age: str | None = None,
        callback: Callable[[str, str, str], typing.Awaitable[None]] | None = None,
    ) -> bool:
        """Runs the copy command asynchronously."""
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

        return await self._run_transfer(cmd, source, dest, callback=callback)

    async def _run_transfer(
        self,
        cmd: list[str],
        source: str,
        dest: str,
        callback: Callable[[str, str, str], typing.Awaitable[None]] | None = None,
    ) -> bool:
        """Helper to run transfer commands and stream logs asynchronously."""
        logger.info(f"Starting transfer: {source} -> {dest}")
        start_time = asyncio.get_running_loop().time()

        # Regex for parsing rclone logs
        re_success = re.compile(r"INFO\s+:\s+(.+?):\s+Copied")
        re_error = re.compile(r"ERROR\s+:\s+(.+?):\s+Failed to copy:\s+(.*)")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stdout and stderr
            )

            if process.stdout:
                while True:
                    line_bytes = await process.stdout.readline()
                    if not line_bytes:
                        break

                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if line:
                        logger.debug(f"[Rclone] {line}")

                        if callback:
                            try:
                                # Check Success
                                m_ok = re_success.search(line)
                                if m_ok:
                                    filename = m_ok.group(1).strip()
                                    await callback(filename, "success", "")
                                    continue

                                # Check Error
                                m_err = re_error.search(line)
                                if m_err:
                                    filename = m_err.group(1).strip()
                                    err_msg = m_err.group(2).strip()
                                    await callback(filename, "failed", err_msg)
                            except Exception as e:
                                logger.error(f"Callback error analyzing line '{line}': {e}")

            await process.wait()

            duration = asyncio.get_running_loop().time() - start_time
            if process.returncode == 0:
                logger.info(f"Transfer completed successfully in {duration:.2f}s")
                return True
            else:
                logger.error(f"Transfer failed with return code {process.returncode}")
                return False

        except asyncio.CancelledError:
            logger.warning("Transfer cancelled. Terminating rclone process...")
            try:
                process.terminate()
                await process.wait()
            except Exception:
                pass
            raise
        except Exception as e:
            logger.error(f"Transfer execution error: {e}")
            return False

    async def list_files(self, remote: str) -> dict[str, int] | None:
        """Lists files on the remote asynchronously."""
        cmd = ["rclone", "lsjson", remote, "--recursive", "--config", self.config_path]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                err_text = stderr.decode()
                if proc.returncode == 3:
                    # Exit code 3 means directory not found.
                    return {}
                logger.error(f"Failed to list remote files: {err_text}")
                return None

            items = json.loads(stdout.decode())
            # Create a simple dict: relative_path -> size
            return {item["Path"]: item["Size"] for item in items if not item["IsDir"]}

        except Exception as e:
            logger.error(f"Failed to list remote files: {e}")
            return None

    def get_disk_usage_percent(self, path: str) -> float:
        """Checks disk usage percentage for the given path (blocking)."""
        # Keep blocking as os.statvfs is fast syscall
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
