import datetime
import glob
import json
import logging

# Logging Config
import logging.handlers
import os
import shutil
import socket
import sys
import time

from mailer import Mailer

os.makedirs("/var/log/silvasonic", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.TimedRotatingFileHandler(
            "/var/log/silvasonic/healthchecker.log",
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("HealthChecker")

# Config
BASE_DIR = "/mnt/data/services/silvasonic"
SERVICES_CONFIG = {
    "uploader": {"name": "Uploader", "timeout": 3600},  # 60 mins
    "recorder": {"name": "Recorder", "timeout": 120},  # 2 mins
    "birdnet": {"name": "BirdNET", "timeout": 300},  # 5 mins
    "livesound": {"name": "Liveaudio", "timeout": 120},  # 2 mins
    "dashboard": {"name": "Dashboard", "timeout": 120},  # 2 mins
    "postgres": {"name": "PostgressDB", "timeout": 300},  # 5 mins
    "controller": {"name": "Controller (Supervisor)", "timeout": 120},
    # "weather": {"name": "Weather Station", "timeout": 300} # 5 mins
}

STATUS_DIR = f"{BASE_DIR}/status"
ERROR_DIR = f"{BASE_DIR}/errors"
ARCHIVE_DIR = f"{BASE_DIR}/errors/archive"
CHECK_INTERVAL = 5  # Check every 5 seconds


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


def check_services_status(mailer: Mailer) -> None:
    """Checks status files for all services and produces a consolidated system status."""
    current_time = time.time()
    system_status = {}

    # Load overrides from settings.json
    timeouts_override = {}
    try:
        config_path = "/config/settings.json"
        if os.path.exists(config_path):
            with open(config_path) as f:
                settings = json.load(f)
                timeouts_override = settings.get("healthchecker", {}).get("service_timeouts", {})
    except Exception as e:
        logger.error(f"Failed to load settings overrides: {e}")

    for service_id, config in SERVICES_CONFIG.items():
        # SKIP hardcoded recorder check, we handle it dynamically below
        if service_id == "recorder":
            continue

        status_file = f"{STATUS_DIR}/{service_id}.json"

        # Determine effective timeout
        timeout_val = timeouts_override.get(service_id, config["timeout"])

        # Default State
        service_data = {
            "id": service_id,
            "name": config["name"],
            "status": "Down",
            "last_seen": 0,
            "message": "No heartbeat found",
            "timeout_threshold": timeout_val,
        }

        # Special Case: Postgres (Probe)
        if service_id == "postgres":
            if check_postgres_connection():
                service_data["status"] = "Running"
                service_data["message"] = "Active (Port 5432 Open)"
                service_data["last_seen"] = current_time
            else:
                service_data["status"] = "Down"
                service_data["message"] = "Connection Failed"
                # Only alert if it persists? For now, standard alert logic.
                msg = "Postgres DB is unreachable."
                logger.error(msg)
                # mailer.send_alert("Postgres Down", msg) # Uncomment if desired, maybe noisy on startup

            system_status[service_id] = service_data
            continue

        if os.path.exists(status_file):
            try:
                with open(status_file) as f:
                    status = json.load(f)

                last_ts = status.get("timestamp", 0)
                service_data["last_seen"] = last_ts

                # Check Timeout
                if current_time - last_ts > timeout_val:
                    msg = f"Service {config['name']} is silent. No heartbeat for {int(current_time - last_ts)} seconds."
                    logger.error(msg)
                    mailer.send_alert(f"{config['name']} Down", msg)

                    service_data["status"] = "Down"
                    service_data["message"] = (
                        f"Timeout ({int(current_time - last_ts)}s > {timeout_val}s)"
                    )
                else:
                    service_data["status"] = "Running"
                    service_data["message"] = "Active"

                # Uploader Special Logic for Alerting
                if service_id == "uploader":
                    last_upload = status.get("last_upload", 0)
                    if current_time - last_upload > 3600:
                        msg = "Uploader running but no upload success for > 60 mins."
                        logger.error(msg)
                        mailer.send_alert("Uploader Stalled", msg)
                        # We updates status too? Maybe 'Warning'?
                        service_data["status"] = "Warning"
                        service_data["message"] = "Stalled (No Upload)"

            except Exception as e:
                logger.error(f"Failed to check status for {service_id}: {e}")
                service_data["message"] = f"Error: {str(e)}"

        system_status[service_id] = service_data

    # --- Dynamic Recorder Discovery ---
    # Find all recorder_*.json files
    recorder_files = glob.glob(f"{STATUS_DIR}/recorder_*.json")
    for rec_file in recorder_files:
        try:
            filename = os.path.basename(rec_file)
            # recorder_front.json -> recorder_front
            rec_id = os.path.splitext(filename)[0]

            with open(rec_file) as f:
                status = json.load(f)

            # Get name from profile if available
            profile_name = status.get("meta", {}).get("profile", {}).get("name", rec_id)

            timeout_val = 120  # Default for recorders
            last_ts = status.get("timestamp", 0)

            rec_data = {
                "id": rec_id,
                "name": f"Recorder ({profile_name})",
                "status": "Running",
                "last_seen": last_ts,
                "message": "Active",
                "timeout_threshold": timeout_val,
            }

            if current_time - last_ts > timeout_val:
                rec_data["status"] = "Down"
                rec_data["message"] = f"Timeout ({int(current_time - last_ts)}s)"
                # Alert logic matching above?

            system_status[rec_id] = rec_data

        except Exception as e:
            logger.error(f"Error processing recorder file {rec_file}: {e}")

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
        logger.error(f"Failed to write system status: {e}")


def check_error_drops(mailer: Mailer) -> None:
    """Checks for new files in the error drop directory."""
    error_files = glob.glob(f"{ERROR_DIR}/*.json")

    if not error_files:
        return

    for err_file in error_files:
        try:
            with open(err_file) as f:
                data = json.load(f)

            logger.info(f"Processing error file: {err_file}")

            subject = f"Critical Error in {data.get('service', 'Unknown Service')}"
            body = f"Context: {data.get('context')}\nError: {data.get('error')}\nTimestamp: {data.get('timestamp')}\n\nFull Dump:\n{json.dumps(data, indent=2)}"

            if mailer.send_alert(subject, body):
                # Move to archive only on success
                filename = os.path.basename(err_file)
                shutil.move(err_file, os.path.join(ARCHIVE_DIR, filename))

        except Exception as e:
            logger.error(f"Failed to process error file {err_file}: {e}")


def write_status() -> None:
    """Writes the HealthChecker's own heartbeat."""
    try:
        import psutil

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
        logger.error(f"Failed to write healthchecker status: {e}")


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
                event = json.load(f)

            logger.info(f"Processing notification event: {os.path.basename(event_file)}")

            if event.get("type") == "bird_detection":
                data = event.get("data", {})
                com_name = data.get("common_name", "Unknown Bird")
                sci_name = data.get("scientific_name", "")
                conf = int(data.get("confidence", 0) * 100)
                time_str = datetime.datetime.fromtimestamp(data.get("start_time", 0)).strftime(
                    "%H:%M:%S"
                )

                subject = f"Bird Alert: {com_name}"
                body = f"Detected {com_name} ({sci_name}) with {conf}% confidence at {time_str}.\n\nListen to the clip."

                # Send the alert!
                if mailer.send_alert(subject, body):
                    os.remove(event_file)  # Consume event
                else:
                    logger.warning(
                        f"Failed to send alert for {event_file}, keeping for retry (or move to error?)"
                    )
                    # For now, maybe move to error to avoid infinite loop if backend down?
                    # Or just keep and retry next loop.
                    # To allow retry, do nothing. But prevent log spam?
                    pass
            else:
                # Unknown event? Remove.
                os.remove(event_file)

        except Exception as e:
            logger.error(f"Failed to process notification {event_file}: {e}")
            try:
                os.remove(event_file)  # Remove bad files
            except OSError:
                pass


def main() -> None:
    """Start the HealthChecker service."""
    logger.info("--- Silvasonic HealthChecker Started ---")
    ensure_dirs()
    mailer = Mailer()

    # Import psutil for status (ensuring it's imported if not global)

    while True:
        try:
            # Re-initialize Mailer to pick up dynamic settings changes (e.g. email)
            mailer = Mailer()

            write_status()  # Heartbeat
            check_services_status(mailer)
            check_error_drops(mailer)
            check_notification_queue(mailer)
        except Exception:
            logger.exception("HealthChecker loop crashed:")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
