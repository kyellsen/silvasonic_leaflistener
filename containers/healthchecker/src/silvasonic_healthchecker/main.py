import datetime
import glob
import json
import logging
import os
import shutil
import signal
import socket
import sys
import time
from types import FrameType
from typing import cast

import psutil
import structlog
from pydantic import ValidationError
from silvasonic_healthchecker.mailer import Mailer
from silvasonic_healthchecker.models import (
    ErrorDrop,
    GlobalSettings,
    NotificationEvent,
    RecorderStatus,
    ServiceConfig,
    ServiceStatus,
)

# --- Structlog Configuration ---
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

# Also configure standard logging for libraries that use it
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

logger = structlog.get_logger()

# Config
BASE_DIR = "/mnt/data/services/silvasonic"
SERVICES_CONFIG = {
    "uploader": ServiceConfig(name="Uploader", timeout=3600),  # 60 mins
    "recorder": ServiceConfig(name="Recorder", timeout=120),  # 2 mins
    "birdnet": ServiceConfig(name="BirdNET", timeout=300),  # 5 mins
    "livesound": ServiceConfig(name="Liveaudio", timeout=120),  # 2 mins
    "dashboard": ServiceConfig(name="Dashboard", timeout=120),  # 2 mins
    "postgres": ServiceConfig(name="PostgressDB", timeout=300),  # 5 mins
    "controller": ServiceConfig(name="Controller (Supervisor)", timeout=120),
    # "weather": ServiceConfig(name="Weather Station", timeout=300) # 5 mins
}

STATUS_DIR = f"{BASE_DIR}/status"
ERROR_DIR = f"{BASE_DIR}/errors"
ARCHIVE_DIR = f"{BASE_DIR}/errors/archive"
CHECK_INTERVAL = 5  # Check every 5 seconds
RECORDER_GHOST_THRESHOLD = 300  # 5 minutes


# Global flag for graceful shutdown
running = True


def signal_handler(signum: int, frame: FrameType | None) -> None:
    """Handle shutdown signals."""
    global running
    logger.info("signal_received", signal=signum, msg="Shutting down gracefully...")
    running = False


def ensure_dirs() -> None:
    """Ensure all required directories exist."""
    for d in [STATUS_DIR, ERROR_DIR, ARCHIVE_DIR]:
        os.makedirs(d, exist_ok=True)


def check_postgres_connection(host: str = "silvasonic_db", port: int = 5432) -> bool:
    """Checks if Postgres is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except OSError:
        return False


def load_timeout_overrides() -> dict[str, int]:
    """Loads timeout overrides from settings.json safely."""
    config_path = "/config/settings.json"
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path) as f:
            content = f.read()
            # Use Pydantic model
            settings: GlobalSettings = GlobalSettings.model_validate_json(content)
            return cast(dict[str, int], settings.healthchecker.service_timeouts)
    except (ValidationError, Exception) as e:
        logger.error("config_load_error", error=str(e))
        return {}


def check_services_status(mailer: Mailer) -> None:
    """Checks status files for all services and produces a consolidated system status."""
    current_time = time.time()
    system_status = {}

    timeouts_override = load_timeout_overrides()

    for service_id, config in SERVICES_CONFIG.items():
        # Special Case: Postgres (Probe)
        if service_id == "postgres":
            service_data = {
                "id": "postgres",
                "name": config.name,
                "status": "Down",
                "last_seen": 0.0,
                "message": "Connection Failed",
                "timeout_threshold": timeouts_override.get("postgres", config.timeout),
            }
            if check_postgres_connection():
                service_data["status"] = "Running"
                service_data["message"] = "Active (Port 5432 Open)"
                service_data["last_seen"] = current_time
            else:
                msg = "Postgres DB is unreachable."
                logger.error("postgres_down", msg=msg)
                # mailer.send_alert("Postgres Down", msg) # Optional: Enable if needed

            system_status["postgres"] = service_data
            continue

        # Dynamic Discovery for all other services
        # Matches: {service_id}.json AND {service_id}_*.json
        # e.g. uploader.json OR uploader_raspberrypi.json
        pattern = f"{STATUS_DIR}/{service_id}*.json"
        found_files = glob.glob(pattern)

        active_instances = 0

        for status_file in found_files:
            filename = os.path.basename(status_file)
            instance_id = os.path.splitext(filename)[0]

            # Ghost Detection (Recorders Only)
            # We only delete "ghost" files for recorders because they are dynamic hardware.
            # For static services (birdnet, uploader), we want to keep the file to show "Timeout" instead of "Missing".
            if service_id == "recorder":
                try:
                    mtime = os.path.getmtime(status_file)
                    file_age = current_time - mtime
                    if file_age > RECORDER_GHOST_THRESHOLD:
                        logger.warning("ghost_recorder_cleanup", file=filename, age=int(file_age))
                        try:
                            os.remove(status_file)
                        except OSError:
                            pass
                        continue  # Skip this file
                except OSError:
                    continue

            try:
                with open(status_file) as f:
                    content = f.read()

                # Validation
                timeout_val = timeouts_override.get(service_id, config.timeout)

                # Determine Model Class
                if service_id == "recorder":
                    status_obj = RecorderStatus.model_validate_json(content)
                    # For recorders, use profile name if available
                    display_name = (
                        f"{config.name} ({status_obj.meta.profile.name})"
                        if status_obj.meta.profile.name
                        else f"{config.name} ({instance_id})"
                    )
                else:
                    status_obj = ServiceStatus.model_validate_json(content)

                    if instance_id == service_id:
                        display_name = config.name
                    else:
                        # Format "uploader_host1" -> "Uploader (host1)"
                        if instance_id.startswith(f"{service_id}_"):
                            suffix = instance_id[len(service_id) + 1 :]
                            display_name = f"{config.name} ({suffix})"
                        else:
                            display_name = f"{config.name} ({instance_id})"

                last_ts = status_obj.timestamp
                time_diff = current_time - last_ts

                service_data = {
                    "id": instance_id,
                    "name": display_name,
                    "status": "Running",
                    "last_seen": last_ts,
                    "message": "Active",
                    "timeout_threshold": timeout_val,
                }

                # Timeout Check
                if time_diff > timeout_val:
                    service_data["status"] = "Down"
                    service_data["message"] = f"Timeout ({int(time_diff)}s > {timeout_val}s)"

                    # Alerting (Only for non-recorders usually, or specific policy)
                    # We avoid spamming alerts for every recorder timeout, but for core services:
                    if service_id != "recorder":
                        msg = f"Service {instance_id} is silent. No heartbeat for {int(time_diff)} seconds."
                        logger.error("service_timeout", service=instance_id, diff=int(time_diff))
                        mailer.send_alert(f"{display_name} Down", msg)

                # Uploader Special Logic
                if service_id == "uploader" and getattr(status_obj, "last_upload", None):
                    last_up = status_obj.last_upload
                    if current_time - last_up > 3600:
                        service_data["status"] = "Warning"
                        service_data["message"] = "Stalled (No Upload)"
                        # Alert logic for stall...

                system_status[instance_id] = service_data
                active_instances += 1

            except ValidationError:
                # Ignore validation errors (e.g. birdnet_stats.json or livesound_sources.json)
                pass
            except Exception as e:
                logger.error("status_read_error", file=filename, error=str(e))

        # Handle Missing Core Services
        # If no instances found for a core service (not recorder), report Down
        if active_instances == 0 and service_id != "recorder":
            system_status[service_id] = {
                "id": service_id,
                "name": config.name,
                "status": "Down",
                "last_seen": 0.0,
                "message": "No instance found",
                "timeout_threshold": timeouts_override.get(service_id, config.timeout),
            }

    # Add HealthChecker itself
    system_status["healthchecker"] = {
        "id": "healthchecker",
        "name": "HealthChecker",
        "status": "Running",
        "last_seen": current_time,
        "message": "Active (Self)",
    }

    # Write Consolidated Status
    try:
        with open(f"{STATUS_DIR}/system_status.json", "w") as f:
            json.dump(system_status, f)
    except Exception as e:
        logger.error("status_write_error", error=str(e))


def check_error_drops(mailer: Mailer) -> None:
    """Checks for new files in the error drop directory."""
    error_files = glob.glob(f"{ERROR_DIR}/*.json")

    if not error_files:
        return

    for err_file in error_files:
        try:
            with open(err_file) as f:
                content = f.read()

            # Validate structure
            data = ErrorDrop.model_validate_json(content)

            logger.info("processing_error_file", file=err_file, service=data.service)

            subject = f"Critical Error in {data.service}"
            # dump generic dict for the body
            full_dump = json.dumps(json.loads(content), indent=2)
            body = f"Context: {data.context}\nError: {data.error}\nTimestamp: {data.timestamp}\n\nFull Dump:\n{full_dump}"

            if mailer.send_alert(subject, body):
                # Move to archive only on success
                filename = os.path.basename(err_file)
                shutil.move(err_file, os.path.join(ARCHIVE_DIR, filename))

        except ValidationError as e:
            logger.error("error_file_validation_failed", file=err_file, error=str(e))
            # Move to archive to avoid loop? Or delete?
            # Let's move to archive with .invalid
            try:
                filename = os.path.basename(err_file)
                shutil.move(err_file, os.path.join(ARCHIVE_DIR, f"{filename}.invalid"))
            except OSError:
                pass
        except Exception as e:
            logger.error("error_file_process_failed", file=err_file, error=str(e))


def write_status() -> None:
    """Writes the HealthChecker's own heartbeat."""
    try:
        data = {
            "service": "healthchecker",
            "timestamp": time.time(),
            "status": "Running",
            "cpu_percent": psutil.cpu_percent(),
            "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
            "pid": os.getpid(),
        }
        status_file = f"{STATUS_DIR}/healthchecker.json"

        tmp_file = f"{status_file}.tmp"
        with open(tmp_file, "w") as f:
            json.dump(data, f)
        os.rename(tmp_file, status_file)
    except Exception as e:
        logger.error("healthchecker_status_write_failed", error=str(e))


NOTIFICATION_DIR = "/data/notifications"


def check_notification_queue(mailer: Mailer) -> None:
    """Processes notification events directly from the queue."""
    if not os.path.exists(NOTIFICATION_DIR):
        return

    # Look for json files
    events = glob.glob(f"{NOTIFICATION_DIR}/*.json")
    for event_file in events:
        try:
            with open(event_file) as f:
                content = f.read()

            # Validate
            event = NotificationEvent.model_validate_json(content)

            logger.info(
                "processing_notification", file=os.path.basename(event_file), type=event.type
            )

            if event.type == "bird_detection":
                data = event.data
                com_name = data.common_name
                sci_name = data.scientific_name
                conf = int(data.confidence * 100)
                time_str = datetime.datetime.fromtimestamp(data.start_time).strftime("%H:%M:%S")

                subject = f"Bird Alert: {com_name}"
                body = f"Detected {com_name} ({sci_name}) with {conf}% confidence at {time_str}.\n\nListen to the clip."

                # Send the alert!
                if mailer.send_alert(subject, body):
                    os.remove(event_file)  # Consume event
                else:
                    logger.warning("alert_send_failed", file=event_file)
            else:
                # Unknown event? Remove.
                logger.warning("unknown_event_type", type=event.type, file=event_file)
                os.remove(event_file)

        except ValidationError as e:
            logger.error("notification_validation_failed", file=event_file, error=str(e))
            os.remove(event_file)  # Consume invalid
        except Exception as e:
            logger.error("notification_process_failed", file=event_file, error=str(e))
            try:
                os.remove(event_file)  # Remove bad files
            except OSError:
                pass


def main() -> None:
    """Start the HealthChecker service."""
    logger.info("startup", msg="Silvasonic HealthChecker Started")

    # Install signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    ensure_dirs()
    mailer = Mailer()

    while running:
        try:
            # Efficient reload check instead of full re-instantiation
            mailer.reload_if_needed()

            write_status()  # Heartbeat
            check_services_status(mailer)
            check_error_drops(mailer)
            check_notification_queue(mailer)
        except Exception:
            logger.exception("main_loop_crash")

        # Sleep in short intervals to be responsive to signals
        for _ in range(CHECK_INTERVAL):
            if not running:
                break
            time.sleep(1)

    logger.info("shutdown", msg="Silvasonic HealthChecker Stopped")


if __name__ == "__main__":
    main()
