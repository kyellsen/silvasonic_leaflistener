import logging

# Setup logging to stdout
import logging.handlers
import os
import sys
import typing

import structlog

from silvasonic_birdnet.watcher import WatcherService

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
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("Main")


def setup_logging() -> None:
    log_dir = os.environ.get("LOG_DIR", "/var/log/silvasonic")
    # Only create directory if we are likely allowed to (e.g. not in a test env that prohibits it)
    # However, for tests, we simply won't call setup_logging or we set LOG_DIR to a temp dir.
    # But wait, main() is not called on import. So this is safe.
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create log directory {log_dir}: {e}", file=sys.stderr)
        # Fallback to just stdout logging if file logging fails?
        # For now, let's proceed with just basicConfig using StreamHandler if file fails or just standard behavior.
        # But for the specific error reported, moving it to main()/setup_logging() solves the import time crash.

    handlers: list[logging.Handler] = []

    # Standard Logger Bridge setup
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

    # 1. Stdout
    s_handler = logging.StreamHandler(sys.stdout)
    s_handler.setFormatter(formatter)
    handlers.append(s_handler)

    # 2. File
    log_file = os.path.join(log_dir, "birdnet.log")
    try:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not setup file logging to {log_file}: {e}", file=sys.stderr)

    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
        force=True,
    )


def main() -> None:
    setup_logging()
    logger.info("Starting Silvasonic BirdNET (Ornithologist)...")

    # Start Watcher (Blocking)
    logger.info("Starting Watcher Service...")
    service = WatcherService()
    service.run()


if __name__ == "__main__":
    main()
