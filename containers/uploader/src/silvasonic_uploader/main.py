import asyncio
import json
import logging
import logging.handlers
import os
import signal
import sys
import time
import typing

import psutil
from silvasonic_uploader.database import DatabaseHandler
from silvasonic_uploader.janitor import StorageJanitor
from silvasonic_uploader.rclone_wrapper import RcloneWrapper

# Configure Logging
logger = logging.getLogger("Uploader")

# Configuration from Env
NEXTCLOUD_URL = os.getenv("UPLOADER_NEXTCLOUD_URL")
NEXTCLOUD_USER = os.getenv("UPLOADER_NEXTCLOUD_USER")
NEXTCLOUD_PASSWORD = os.getenv("UPLOADER_NEXTCLOUD_PASSWORD")
SOCKET_HOSTNAME = __import__("socket").gethostname()
SENSOR_ID = os.getenv("SENSOR_ID", SOCKET_HOSTNAME)

# Base Target Dir (e.g. "silvasonic")
BASE_TARGET_DIR = os.getenv("UPLOADER_TARGET_DIR", "silvasonic")

# Final Target Dir: silvasonic/<sensor_id>
TARGET_DIR = f"{BASE_TARGET_DIR}/{SENSOR_ID}"

SOURCE_DIR = "/data/recording"
SYNC_INTERVAL = int(os.getenv("UPLOADER_SYNC_INTERVAL", 10))
STATUS_FILE = "/mnt/data/services/silvasonic/status/uploader.json"
ERROR_DIR = "/mnt/data/services/silvasonic/errors"
CLEANUP_THRESHOLD = int(os.getenv("UPLOADER_CLEANUP_THRESHOLD", 70))
CLEANUP_TARGET = int(os.getenv("UPLOADER_CLEANUP_TARGET", 60))
MIN_AGE = os.getenv("UPLOADER_MIN_AGE", "1m")


def setup_environment() -> None:
    """Setup logging and directories."""
    os.makedirs("/var/log/silvasonic", exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.handlers.TimedRotatingFileHandler(
                "/var/log/silvasonic/uploader.log",
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8",
            ),
        ],
    )

    # Ensure directories exist
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    os.makedirs(ERROR_DIR, exist_ok=True)


def calculate_queue_size(directory: str, db: typing.Any) -> int:
    """Calculate pending files (local files - uploaded files) using Set Diff.

    This version avoids building a massive list of all local files in memory.
    """
    queue_count = 0
    try:
        # 1. Get Set of ALL uploaded files from DB (O(1) lookup)
        # This might be large (50MB for 500k files), but better than list overhead
        uploaded_set = db.get_all_uploaded_set()

        # 2. Iterate filesystem without building a list
        # Using a generator to walk
        for root, _, filenames in os.walk(directory):
            for f in filenames:
                rel_path = os.path.relpath(os.path.join(root, f), directory)

                # 3. Check membership
                if rel_path not in uploaded_set:
                    queue_count += 1

    except Exception as e:
        logger = logging.getLogger("Uploader")  # Re-get logger cleanly
        logger.error(f"Failed to calculate queue size: {e}")
        return 0

    return queue_count


def write_status(
    status: str, last_upload: float = 0, queue_size: int = -1, disk_usage: float = 0
) -> None:
    """Write current status to JSON file for dashboard. Blocking IO."""
    try:
        data = {
            "service": "uploader",
            "timestamp": time.time(),
            "status": status,
            "cpu_percent": psutil.cpu_percent(),
            "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
            "meta": {
                "last_upload": last_upload,
                "queue_size": queue_size,
                "disk_usage_percent": disk_usage,
            },
            # Keeping top-level for backwards compat if needed temporarily,
            # but dashboard should update
            "last_upload": last_upload,
            "pid": os.getpid(),
        }
        # Atomic write
        tmp_file = f"{STATUS_FILE}.tmp"
        with open(tmp_file, "w") as f:
            json.dump(data, f)
        os.rename(tmp_file, STATUS_FILE)
    except Exception as e:
        logger.error(f"Failed to write status: {e}")


def report_error(context: str, error: Exception) -> None:
    """Write critical error to shared error directory."""
    try:
        timestamp = int(time.time())
        filename = f"{ERROR_DIR}/error_uploader_{timestamp}.json"

        data = {
            "service": "uploader",
            "timestamp": timestamp,
            "context": context,
            "error": str(error),
            "pid": os.getpid(),
        }

        with open(filename, "w") as f:
            json.dump(data, f)

        logger.error(f"Critical error reported to {filename}")
    except Exception as ie:
        logger.error(f"Failed to report error: {ie}")


async def main_loop() -> None:
    """Main async loop."""
    logger.info("--- Silvasonic Uploader (AsyncIO Edition) ---")

    loop = asyncio.get_running_loop()

    wrapper = RcloneWrapper()
    janitor = StorageJanitor(
        SOURCE_DIR, threshold_percent=CLEANUP_THRESHOLD, target_percent=CLEANUP_TARGET
    )
    db = DatabaseHandler()

    # Database Connection (Blocking, run in executor if slow, but usually fast enough for init)
    # We loop here to ensure DB is up
    while True:
        try:
            # Run connect in executor to be safe against timeouts blocking the loop
            connected = await loop.run_in_executor(None, db.connect)
            if connected:
                break
        except Exception as e:
            logger.error(f"DB Connect Error: {e}")

        logger.warning(f"Database not accessible at {db.host}:{db.port}. Retrying in 5s...")
        await asyncio.sleep(5)

    # 1. Configuration Check
    if NEXTCLOUD_URL and NEXTCLOUD_USER and NEXTCLOUD_PASSWORD:
        await wrapper.configure_webdav(
            remote_name="remote",
            url=NEXTCLOUD_URL,
            user=NEXTCLOUD_USER,
            password=NEXTCLOUD_PASSWORD,
        )
    else:
        logger.warning("Environment variables missing. Assuming config file already exists.")

    last_upload_success: float = 0.0

    while True:
        try:
            if os.path.exists(SOURCE_DIR):
                # Gather Metrics (Blocking IO -> thread)
                # Note: creating short lived session for queue size calculation if needed?
                # calculate_queue_size manages its own session/connection usage via db methods
                queue_size = await loop.run_in_executor(None, calculate_queue_size, SOURCE_DIR, db)
                disk_usage = await loop.run_in_executor(
                    None, wrapper.get_disk_usage_percent, SOURCE_DIR
                )

                # --- PHASE 1: UPLOAD ---
                await loop.run_in_executor(
                    None, write_status, "Syncing", last_upload_success, queue_size, disk_usage
                )

                # Context Manager for DB Session Reuse
                # get_session is sync context manager. We open it here.
                # Note: This holds a DB connection open during the entire upload phase.
                # This is efficient (1 connection vs N connections) but holds resource.
                # Given uploader's dedicated role, this is correct pattern.
                try:
                    with db.get_session() as session:

                        async def upload_callback_async(
                            filename: str, status: str, error: str
                        ) -> None:
                            """Async callback that schedules sync DB write."""
                            try:
                                # Get file size if success (Blocking stat)
                                size = 0
                                if status == "success":
                                    full_path = os.path.join(SOURCE_DIR, filename)
                                    if os.path.exists(full_path):
                                        # os.path.getsize is fast, but technically blocking.
                                        # For standard SSD/SD, acceptable.
                                        size = os.path.getsize(full_path)

                                def db_update() -> None:
                                    db.log_upload(
                                        filename=filename,
                                        remote_path=f"{TARGET_DIR}/{filename}",
                                        status=status,
                                        size_bytes=size,
                                        error_message=error,
                                        session=session,
                                    )
                                    # Commit immediately for dashboard visibility
                                    session.commit()

                                # Execute in thread pool
                                await loop.run_in_executor(None, db_update)

                            except Exception as e:
                                logger.error(f"Callback error: {e}")

                        # Use COPY instead of SYNC to prevent deleting files on remote
                        success = await wrapper.copy(
                            SOURCE_DIR,
                            f"remote:{TARGET_DIR}",
                            min_age=MIN_AGE,
                            callback=upload_callback_async,
                        )

                except Exception as e:
                    logger.error(f"Session/Upload error: {e}")
                    success = False

                # Update metrics
                queue_size = await loop.run_in_executor(None, calculate_queue_size, SOURCE_DIR, db)
                disk_usage = await loop.run_in_executor(
                    None, wrapper.get_disk_usage_percent, SOURCE_DIR
                )

                if success:
                    last_upload_success = time.time()
                    await loop.run_in_executor(
                        None, write_status, "Idle", last_upload_success, queue_size, disk_usage
                    )

                    # --- PHASE 2: CLEANUP ---
                    await loop.run_in_executor(
                        None, write_status, "Cleaning", last_upload_success, queue_size, disk_usage
                    )

                    # List Remote Files (Async rclone)
                    remote_files = await wrapper.list_files(f"remote:{TARGET_DIR}")

                    # Run cleanup (Blocking IO -> thread)
                    # We pass wrapper.get_disk_usage_percent as callback
                    await loop.run_in_executor(
                        None, janitor.check_and_clean, remote_files, wrapper.get_disk_usage_percent
                    )

                    # Final update
                    queue_size = await loop.run_in_executor(
                        None, calculate_queue_size, SOURCE_DIR, db
                    )
                    disk_usage = await loop.run_in_executor(
                        None, wrapper.get_disk_usage_percent, SOURCE_DIR
                    )
                    await loop.run_in_executor(
                        None, write_status, "Idle", last_upload_success, queue_size, disk_usage
                    )
                else:
                    logger.error("Upload failed. Validation and cleanup skipped.")
                    await loop.run_in_executor(
                        None,
                        write_status,
                        "Error: Upload Failed",
                        last_upload_success,
                        queue_size,
                        disk_usage,
                    )

            else:
                logger.error(f"Source directory {SOURCE_DIR} does not exist!")
                await loop.run_in_executor(
                    None, write_status, "Error: No Source", last_upload_success
                )

            logger.info(f"Sleeping for {SYNC_INTERVAL} seconds...")
            # We can just await sleep, it is cancellable
            await asyncio.sleep(SYNC_INTERVAL)

        except asyncio.CancelledError:
            logger.info("Main loop cancelled. Shutting down...")
            raise
        except Exception as e:
            logger.exception("Unexpected error in main loop:")
            report_error("main_loop_crash", e)
            try:
                await loop.run_in_executor(
                    None, write_status, "Error: Crashed", last_upload_success
                )
            except Exception:
                pass
            await asyncio.sleep(60)


def main() -> None:
    setup_environment()

    # Run async main
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        # Should be handled by CancelledError inside run usually,
        # but if we catch it here it's cleaner output
        pass
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Signal handling in asyncio.run handles SIGINT/SIGTERM by cancelling tasks?
    # Actually asyncio.run doesn't handle SIGTERM by default on all platforms the same way.
    # But on Linux/Docker, we want to catch SIGTERM and cancel the loop.
    # However, asyncio.run() creates a loop. We can add signal handlers inside main_loop.
    # But let's keep it simple: Standard asyncio.run handles KeyboardInterrupt (SIGINT).
    # For SIGTERM (Docker stop), we need to register a handler.

    # We'll use a slightly more manual approach to ensure SIGTERM works.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    main_task = loop.create_task(main_loop())

    def shutdown_handler() -> None:
        logger.info("Received signal to stop.")
        main_task.cancel()

    loop.add_signal_handler(signal.SIGTERM, shutdown_handler)
    loop.add_signal_handler(signal.SIGINT, shutdown_handler)

    try:
        loop.run_until_complete(main_task)
    except asyncio.CancelledError:
        pass  # Clean exit
    except Exception as e:
        logger.critical(f"Fatal startup error: {e}")
    finally:
        loop.close()
        logger.info("Uploader service stopped.")
