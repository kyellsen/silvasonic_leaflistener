import asyncio
import json
import logging
import logging.handlers
import os
import sys
import time
import typing
from contextlib import asynccontextmanager

import psutil
import structlog
import uvicorn
from fastapi import FastAPI
from silvasonic_uploader.api import router as api_router
from silvasonic_uploader.api import set_reloader
from silvasonic_uploader.config import UploaderSettings
from silvasonic_uploader.database import DatabaseHandler
from silvasonic_uploader.janitor import StorageJanitor
from silvasonic_uploader.rclone_wrapper import RcloneWrapper

# --- Logging Configuration ---
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

logger = structlog.get_logger("Uploader")

# --- Globals for Service Management ---
_service_task: asyncio.Task | None = None
_current_settings: UploaderSettings | None = None
_db_handler: DatabaseHandler | None = None

# Global Status State
_last_error: str | None = None
_last_error_time: float | None = None

STATUS_FILE_TEMPLATE = "/mnt/data/services/silvasonic/status/uploader_{sensor_id}.json"
ERROR_DIR = "/mnt/data/services/silvasonic/errors"


def setup_logging() -> None:
    """Setup logging handlers."""
    os.makedirs("/var/log/silvasonic", exist_ok=True)

    pre_chain: list[typing.Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=pre_chain,
    )

    handlers: list[logging.Handler] = []

    # Stdout
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    handlers.append(stream)

    # File
    fhandler = logging.handlers.TimedRotatingFileHandler(
        "/var/log/silvasonic/uploader.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    fhandler.setFormatter(formatter)
    handlers.append(fhandler)

    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


def calculate_queue_size(directory: str, db: typing.Any) -> int:
    """Calculate pending files (local files - uploaded files) manually."""
    queue_count = 0
    try:
        if not os.path.exists(directory):
            return 0

        uploaded_set = db.get_all_uploaded_set()
        for root, _, filenames in os.walk(directory):
            for f in filenames:
                rel_path = os.path.relpath(os.path.join(root, f), directory)
                if rel_path not in uploaded_set:
                    queue_count += 1
    except Exception as e:
        # Create a fresh logger since this runs in a thread
        lgr = logging.getLogger("Uploader")
        lgr.error(f"Failed to calculate queue size: {e}")
        return 0
    return queue_count


def write_status(
    status: str,
    sensor_id: str,
    last_upload: float = 0,
    queue_size: int = -1,
    disk_usage: float = 0,
    error: Exception | str | None = None,
    progress: dict[str, typing.Any] | None = None,
) -> None:
    """Write current status to JSON file for dashboard."""
    try:
        global _last_error, _last_error_time
        if error:
            _last_error = str(error)
            _last_error_time = time.time()

        status_file = STATUS_FILE_TEMPLATE.format(sensor_id=sensor_id)

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
            "last_error": _last_error,
            "last_error_time": _last_error_time,
            "last_upload": last_upload,
            "pid": os.getpid(),
        }

        if progress:
            data["meta"]["progress"] = progress

        # Atomic write
        os.makedirs(os.path.dirname(status_file), exist_ok=True)
        tmp_file = f"{status_file}.tmp"
        with open(tmp_file, "w") as f:
            json.dump(data, f)
        os.rename(tmp_file, status_file)
    except Exception as e:
        logger.error(f"Failed to write status: {e}")


def report_error(context: str, error: Exception) -> None:
    """Write critical error to shared error directory."""
    try:
        os.makedirs(ERROR_DIR, exist_ok=True)
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


async def service_loop(settings: UploaderSettings) -> None:
    """The main business logic loop."""
    logger.info(f"Starting service loop with interval {settings.sync_interval}s")

    # Constants from settings
    source_dir = "/data/recording"
    target_dir = f"{settings.target_dir}/{settings.sensor_id}"

    # Initialize components
    wrapper = RcloneWrapper()
    janitor = StorageJanitor(
        source_dir,
        threshold_percent=settings.cleanup_threshold,
        target_percent=settings.cleanup_target,
    )

    # Re-use global DB handler if available, else create new
    global _db_handler
    if _db_handler is None:
        _db_handler = DatabaseHandler()
    db = _db_handler

    loop = asyncio.get_running_loop()

    # Ensure DB is connected
    while True:
        try:
            connected = await loop.run_in_executor(None, db.connect)
            if connected:
                break
        except Exception as e:
            logger.error(f"DB Connect Error: {e}")
        logger.warning("Waiting for DB...")
        await asyncio.sleep(5)

    # Configure Remote
    if settings.nextcloud_url and settings.nextcloud_user and settings.nextcloud_password:
        await wrapper.configure_webdav(
            remote_name="remote",
            url=settings.nextcloud_url,
            user=settings.nextcloud_user,
            password=settings.nextcloud_password.get_secret_value(),
        )
    else:
        logger.warning("Nextcloud credentials incomplete. Skipping remote config.")

    last_upload_success: float = 0.0

    try:
        while True:
            # Check for cancellation
            if asyncio.current_task().cancelled():
                raise asyncio.CancelledError()

            try:
                if os.path.exists(source_dir):
                    # Metrics
                    queue_size = await loop.run_in_executor(
                        None, calculate_queue_size, source_dir, db
                    )
                    disk_usage = await loop.run_in_executor(
                        None, wrapper.get_disk_usage_percent, source_dir
                    )

                    batch_total = queue_size
                    batch_processed = 0
                    last_status_update = 0.0

                    # Update Status: Syncing
                    await loop.run_in_executor(
                        None,
                        write_status,
                        "Syncing",
                        settings.sensor_id,
                        last_upload_success,
                        queue_size,
                        disk_usage,
                    )

                    success = False

                    # Upload Logic
                    try:
                        with db.get_session() as session:

                            async def upload_callback(
                                filename: str,
                                status: str,
                                error: str,
                                # bind vars to avoid B023
                                batch_total: int = batch_total,
                                last_upload_success: float = last_upload_success,
                                disk_usage: float = disk_usage,
                            ) -> None:
                                nonlocal batch_processed, queue_size, last_status_update
                                try:
                                    size = 0
                                    if status == "success":
                                        full_path = os.path.join(source_dir, filename)
                                        if os.path.exists(full_path):
                                            size = os.path.getsize(full_path)

                                    # Log to DB
                                    def db_task():
                                        db.log_upload(
                                            filename=filename,
                                            remote_path=f"{target_dir}/{filename}",
                                            status=status,
                                            size_bytes=size,
                                            error_message=error,
                                            session=session,
                                        )
                                        session.commit()

                                    await loop.run_in_executor(None, db_task)

                                    # Update Progress
                                    batch_processed += 1
                                    if status == "success":
                                        queue_size = max(0, queue_size - 1)

                                    # Write status (throttled)
                                    now = time.time()
                                    if now - last_status_update > 1.0:
                                        percent = 0.0
                                        if batch_total > 0:
                                            percent = round(
                                                (batch_processed / batch_total) * 100, 1
                                            )

                                        progress_data = {
                                            "batch_total": batch_total,
                                            "batch_processed": batch_processed,
                                            "percent": percent,
                                        }

                                        await loop.run_in_executor(
                                            None,
                                            write_status,
                                            "Syncing",
                                            settings.sensor_id,
                                            last_upload_success,
                                            queue_size,
                                            disk_usage,
                                            None,
                                            progress_data,
                                        )
                                        last_status_update = now

                                except Exception as e:
                                    logger.error(f"Callback error: {e}")

                            # Execute Copy
                            success = await wrapper.copy(
                                source_dir,
                                f"remote:{target_dir}",
                                min_age=settings.min_age,
                                bwlimit=settings.bwlimit,
                                callback=upload_callback,
                            )

                    except Exception as e:
                        logger.error(f"Upload session error: {e}")

                    # Post-Upload Metadata Refresh
                    queue_size = await loop.run_in_executor(
                        None, calculate_queue_size, source_dir, db
                    )
                    disk_usage = await loop.run_in_executor(
                        None, wrapper.get_disk_usage_percent, source_dir
                    )

                    if success:
                        last_upload_success = time.time()

                        # Cleanup Phase
                        await loop.run_in_executor(
                            None,
                            write_status,
                            "Cleaning",
                            settings.sensor_id,
                            last_upload_success,
                            queue_size,
                            disk_usage,
                        )

                        remote_files = await wrapper.list_files(f"remote:{target_dir}")
                        await loop.run_in_executor(
                            None,
                            janitor.check_and_clean,
                            remote_files,
                            wrapper.get_disk_usage_percent,
                        )

                        # Final Idle Status
                        queue_size = await loop.run_in_executor(
                            None, calculate_queue_size, source_dir, db
                        )
                        disk_usage = await loop.run_in_executor(
                            None, wrapper.get_disk_usage_percent, source_dir
                        )
                        await loop.run_in_executor(
                            None,
                            write_status,
                            "Idle",
                            settings.sensor_id,
                            last_upload_success,
                            queue_size,
                            disk_usage,
                        )
                    else:
                        await loop.run_in_executor(
                            None,
                            write_status,
                            "Error: Upload Failed",
                            settings.sensor_id,
                            last_upload_success,
                            queue_size,
                            disk_usage,
                        )

                else:
                    logger.warning(f"Source dir {source_dir} not found.")
                    await loop.run_in_executor(
                        None,
                        write_status,
                        "Error: No Source",
                        settings.sensor_id,
                        last_upload_success,
                        -1,
                        0,
                        f"{source_dir} missing",
                    )

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("Error in loop iteration")
                report_error("loop_iteration", e)

            await asyncio.sleep(settings.sync_interval)

    except asyncio.CancelledError:
        logger.info("Service loop cancelled.")
        raise
    except Exception as e:
        logger.exception("Service loop crashed")
        report_error("service_loop_crash", e)


async def reload_service() -> None:
    """Reloads the service task with new settings."""
    global _service_task, _current_settings
    logger.info("Reloading service...")

    # 1. Cancel existing task
    if _service_task:
        _service_task.cancel()
        try:
            await _service_task
        except asyncio.CancelledError:
            pass
        _service_task = None

    # 2. Reload settings
    _current_settings = UploaderSettings.load()

    # 3. Start new task
    _service_task = asyncio.create_task(service_loop(_current_settings))
    logger.info("Service reloaded successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()

    # Inject reloader into API
    set_reloader(reload_service)

    # Initial Start
    global _current_settings, _service_task
    _current_settings = UploaderSettings.load()
    _service_task = asyncio.create_task(service_loop(_current_settings))

    yield

    # Shutdown
    if _service_task:
        _service_task.cancel()
        try:
            await _service_task
        except asyncio.CancelledError:
            pass


# --- FastAPI App ---
app = FastAPI(title="Silvasonic Uploader", lifespan=lifespan)
app.include_router(api_router)


def main() -> None:
    """Entry point."""
    uvicorn.run(app, host="0.0.0.0", port=8001, log_config=None)


if __name__ == "__main__":
    main()
