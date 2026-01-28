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
import redis
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


def check_services_status(mailer: Mailer, service_states: dict[str, str]) -> None:
    """Checks Redis status keys for all services and produces a consolidated system status."""
    current_time = time.time()
    system_status = {}

    timeouts_override = load_timeout_overrides()

    # Lazy Redis connection
    try:
        r = redis.Redis(host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=2)
        # Scan for all status keys
        keys = r.keys("status:*")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return

    # Process all keys found in Redis
    # Map them to service definitions
    # Keys format: status:<service_type>:<id> or status:<service_type>

    # We first collect all found statuses
    found_services = set()

    for k in keys:
        try:
            key_str = k.decode("utf-8")
            content = r.get(key_str)
            if not content:
                continue

            # Parse Key
            parts = key_str.split(":")
            # parts[0] is 'status'
            service_type = parts[1]

            # Determine Instance ID
            if len(parts) > 2:
                # e.g. status:recorder:front -> recorder_front
                # e.g. status:uploader:sensor1 -> uploader_sensor1
                instance_suffix = "_".join(parts[2:])
                instance_id = f"{service_type}_{instance_suffix}"
            else:
                instance_id = service_type

            # Config Lookup
            if service_type in SERVICES_CONFIG:
                config = SERVICES_CONFIG[service_type]
            else:
                # Unknown service type, maybe new?
                continue

            found_services.add(service_type)

            # Determine Display Name & Model
            if service_type == "recorder":
                status_obj = RecorderStatus.model_validate_json(content)
                display_name = (
                    f"{config.name} ({status_obj.meta.profile.name})"
                    if status_obj.meta.profile.name
                    else f"{config.name} ({instance_id})"
                )
            else:
                status_obj = ServiceStatus.model_validate_json(content)
                if instance_id == service_type:
                    display_name = config.name
                else:
                    # e.g. uploader_sensor1 -> Uploader (sensor1)
                    if instance_id.startswith(f"{service_type}_"):
                        suffix = instance_id[len(service_type) + 1 :]
                        display_name = f"{config.name} ({suffix})"
                    else:
                        display_name = f"{config.name} ({instance_id})"

            last_ts = status_obj.timestamp
            time_diff = current_time - last_ts
            timeout_val = timeouts_override.get(service_type, config.timeout)

            # --- Status Logic ---
            source_message = getattr(status_obj, "message", None)
            final_message = source_message if source_message else "Active"

            service_data = {
                "id": instance_id,
                "name": display_name,
                "status": "Running",
                "last_seen": last_ts,
                "message": final_message,
                "timeout_threshold": timeout_val,
            }

            if getattr(status_obj, "state", None):
                service_data["state"] = status_obj.state

            # Timeout Logic (Redis TTL handles cleanup, but if key exists it might be stale if strict consistency is needed?
            # Redis TTL removes key. If key is here, it is likely valid.
            # But let's check timestamp just in case clock drift or manual set without TTL.
            if time_diff > timeout_val:
                service_data["status"] = "Down"
                service_data["message"] = f"Timeout ({int(time_diff)}s > {timeout_val}s)"

            # State Transition Logic
            prev_status = service_states.get(instance_id, "Unknown")
            curr_status = service_data["status"]

            if curr_status == "Down" and prev_status != "Down":
                # Down alert
                if service_type != "recorder":
                    msg = f"Service {instance_id} timed out."
                    logger.error("service_down", service=instance_id)
                    mailer.send_alert(f"{display_name} Down", msg)
            elif curr_status == "Running" and prev_status == "Down":
                # Recovery alert
                if service_type != "recorder":
                    logger.info("service_recovered", service=instance_id)
                    mailer.send_alert(f"{display_name} Recovered", "Service is online.")

            service_states[instance_id] = curr_status
            system_status[instance_id] = service_data

        except Exception as e:
            logger.error(f"Error processing key {k}: {e}")

    # Check for Missing Core Services (that we expect but didn't find keys for)
    for service_id, config in SERVICES_CONFIG.items():
        if service_id == "postgres":
            continue  # Handled separately below/above?
            # Wait, original code handled postgres at top of loop. We missed it.
            # We should add postgres check back.

        # Postgres Check (Re-adding logic from original)
        if service_id == "postgres":
            # See logic below
            pass
        elif service_id not in found_services and service_id != "recorder":
            # Core service missing entirely
            # (Recorder is dynamic, so 0 recorders is valid? Original logic says: if active_instances == 0 and != recorder)
            # Here 'found_services' tracks types.

            system_status[service_id] = {
                "id": service_id,
                "name": config.name,
                "status": "Down",
                "last_seen": 0.0,
                "message": "No instance found (Redis key missing)",
                "timeout_threshold": timeouts_override.get(service_id, config.timeout),
            }
            if service_states.get(service_id) != "Down":
                logger.error("service_missing", service=service_id)
                mailer.send_alert(f"{config.name} Down", "No instance found.")
            service_states[service_id] = "Down"

    # Re-integrate Postgres Check
    p_conf = SERVICES_CONFIG["postgres"]
    p_data = {
        "id": "postgres",
        "name": p_conf.name,
        "status": "Down",
        "last_seen": 0.0,
        "message": "Connection Failed",
        "timeout_threshold": timeouts_override.get("postgres", p_conf.timeout),
    }
    if check_postgres_connection():
        p_data["status"] = "Running"
        p_data["message"] = "Active"
        p_data["last_seen"] = current_time

    if p_data["status"] == "Down" and service_states.get("postgres") != "Down":
        mailer.send_alert("Postgres Down", "DB Unreachable")

    service_states["postgres"] = p_data["status"]
    system_status["postgres"] = p_data

    # Add HealthChecker itself
    system_status["healthchecker"] = {
        "id": "healthchecker",
        "name": "HealthChecker",
        "status": "Running",
        "last_seen": current_time,
        "message": "Active (Self)",
    }

    # Write Consolidated Status to Redis AND File (for compat)
    try:
        # File (Legacy)
        with open(f"{STATUS_DIR}/system_status.json", "w") as f:
            json.dump(system_status, f)

        # Redis (Modern)
        # Use a single key for full system status? Or just let Dashboard aggregate?
        # User requested "modern in-memory".
        # Writing system_status to Redis is useful for the dashboard main view.
        r.set("system:status", json.dumps(system_status))

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
    """Writes the HealthChecker's own heartbeat to Redis."""
    try:
        data = {
            "service": "healthchecker",
            "timestamp": time.time(),
            "status": "Running",
            "cpu_percent": psutil.cpu_percent(),
            "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
            "pid": os.getpid(),
        }

        r = redis.Redis(host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=2)
        r.setex("status:healthchecker", 10, json.dumps(data))

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

    service_states: dict[str, str] = {}

    while running:
        try:
            # Efficient reload check instead of full re-instantiation
            mailer.reload_if_needed()

            write_status()  # Heartbeat
            check_services_status(mailer, service_states)
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
