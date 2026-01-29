import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import types

import redis
import structlog
from silvasonic_uploader.config import UploaderSettings
from silvasonic_uploader.database import DatabaseHandler
from silvasonic_uploader.rclone_wrapper import RcloneWrapper

# Configure Logging
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
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = structlog.get_logger("uploader")

shutdown_event = threading.Event()


def signal_handler(signum: int, frame: types.FrameType | None) -> None:
    logger.info("Shutdown signal received")
    shutdown_event.set()


def compress_to_flac(input_path: str) -> str | None:
    """Compress WAV to FLAC using ffmpeg. Returns path to FLAC or None."""
    if not os.path.exists(input_path):
        return None

    # Check if already FLAC?
    if input_path.endswith(".flac"):
        return input_path

    output_path = input_path.rsplit(".", 1)[0] + ".flac"

    # If output exists, overwrite?

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-c:a",
        "flac",
        "-compression_level",
        "5",
        "-v",
        "error",
        output_path,
    ]

    try:
        subprocess.run(cmd, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FLAC compression failed for {input_path}: {e}")
        return None


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Silvasonic Uploader V2 Starting...")

    UploaderSettings.load()
    db = DatabaseHandler()
    RcloneWrapper()

    # Configure Rclone Remote
    remote = os.getenv("RCLONE_REMOTE", "remote")

    # Wait for DB
    while not shutdown_event.is_set():
        if db.connect():
            break
        logger.warning("Waiting for DB connection...")
        time.sleep(5)

    # Redis Connection
    r = redis.Redis(host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=2)

    RcloneWrapper()

    # Main Loop
    last_heartbeat = 0.0
    last_upload_ts = 0.0

    while not shutdown_event.is_set():
        # Heartbeat (Every 10s)
        now = time.time()
        if now - last_heartbeat > 10:
            try:
                # 1. Get Queue Size
                queue_size = db.count_pending_recordings()

                # 2. Get Disk Usage (Check /recordings or fallback to current dir)
                check_dir = "/recordings" if os.path.exists("/recordings") else "."
                if os.path.exists(check_dir):
                    total, used, free = shutil.disk_usage(check_dir)
                    disk_usage_percent = (used / total) * 100
                else:
                    disk_usage_percent = 0.0

                # 3. Construct Payload
                payload = {
                    "status": "online",
                    "last_upload": last_upload_ts,
                    "meta": {
                        "queue_size": queue_size,
                        "disk_usage_percent": disk_usage_percent,
                        "last_upload": last_upload_ts,
                    },
                }

                r.set("status:uploader", json.dumps(payload), ex=30)
                last_heartbeat = now
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                pass  # Ignore redis errors

        try:
            pending = db.get_pending_recordings(limit=5)

            if not pending:
                time.sleep(10)
                continue

            logger.info(f"Found {len(pending)} pending uploads.")

            for rec in pending:
                if shutdown_event.is_set():
                    break

                # Prefer High Res, fallback to Low
                src_path = rec.get("path_high") or rec.get("path_low")
                if not src_path:
                    logger.warning(f"Recording {rec['id']} has no paths!", id=rec["id"])
                    # Mark uploaded to skip?
                    continue

                if not os.path.exists(src_path):
                    logger.warning(f"File missing: {src_path}", id=rec["id"])
                    # Mark uploaded to skip/avoid loop?
                    # db.mark_recording_uploaded(rec['id'])
                    continue

                # Compress
                flac_path = compress_to_flac(src_path)
                if not flac_path:
                    continue

                filename = os.path.basename(flac_path)

                # Upload

                logger.info(f"Uploading {filename}...")

                # Use our sync method (which uses async, so we looprunner it or just use subprocess here?)
                # RcloneWrapper is async. We are in sync main.
                # Let's use asyncio.run or just subprocess directly if simpler.
                # RcloneWrapper uses asyncio.

                # Quick synchronous rclone call for simplicity in this loop
                cmd = ["rclone", "copy", flac_path, f"{remote}:recordings/"]
                # Add config?
                # Using RcloneWrapper methods is better but needs event loop.
                # Let's just spawn rclone process directly for robustness in this simple loop

                res = subprocess.run(cmd, capture_output=True)

                if res.returncode == 0:
                    logger.info(f"Uploaded {filename}")
                    db.mark_recording_uploaded(rec["id"])

                    last_upload_ts = time.time()

                    # Delete temp flac if we created it
                    if flac_path != src_path:
                        os.remove(flac_path)
                else:
                    error_msg = res.stderr.decode()
                    logger.error(f"Upload failed: {error_msg}")

        except Exception:
            logger.exception("Uploader Loop Error")
            time.sleep(10)


if __name__ == "__main__":
    main()
