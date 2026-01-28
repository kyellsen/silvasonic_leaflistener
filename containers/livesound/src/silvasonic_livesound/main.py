import json
import logging
import logging.handlers
import os
import sys
import threading
import time
import typing

import psutil
import structlog

from .config import settings

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

# Bridge Setup
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
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
handlers.append(sh)

os.makedirs("/var/log/silvasonic", exist_ok=True)

try:
    # Use config dir or fallback
    log_file = os.path.join(settings.LOG_DIR or "/var/log/silvasonic", "sound_analyser.log")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)
except Exception as e:
    # Can't log yet fully
    print(f"Failed to setup file logging: {e}", file=sys.stderr)

logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)

logger = structlog.get_logger("Main")

# Global Error State
_last_error: str | None = None
_last_error_time: float | None = None


def write_status() -> None:
    """Writes the Livesound's own heartbeat."""
    status_file = settings.STATUS_FILE
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    while True:
        try:
            global _last_error, _last_error_time
            data = {
                "service": "livesound",
                "timestamp": time.time(),
                "status": "Running" if not _last_error else "Error: Degraded",
                "last_error": _last_error,
                "last_error_time": _last_error_time,
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "pid": os.getpid(),
            }

            tmp_file = f"{status_file}.tmp"
            with open(tmp_file, "w") as f:
                json.dump(data, f)
            os.rename(tmp_file, status_file)
        except Exception as e:
            logger.error(f"Failed to write livesound status: {e}")

        time.sleep(5)


def main() -> None:
    logger.info("Starting Silvasonic Livesound...")

    # Start Status Thread
    t = threading.Thread(target=write_status, daemon=True)
    t.start()

    # Start Live Server (Blocking Main Process)
    logger.info("Starting Live Server (Uvicorn)...")
    import uvicorn

    # Loading via string to allow reload support if mapped, though we run direct here
    try:
        uvicorn.run(
            "silvasonic_livesound.live.server:app",
            host=settings.HOST,
            port=settings.PORT,
            log_level="info",
        )
    except Exception as e:
        logger.critical(f"Livesound Main Crash: {e}")
        global _last_error, _last_error_time
        _last_error = str(e)
        _last_error_time = time.time()
        # Give the status thread a chance to write the error
        time.sleep(6)
        raise


if __name__ == "__main__":
    main()
