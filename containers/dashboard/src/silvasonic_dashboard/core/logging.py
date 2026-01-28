import logging
import logging.handlers
import os
import sys
import typing

import structlog

# Setup structlog
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


def setup_logging() -> None:
    """Configure logging for the dashboard service."""
    # Initialize Paths with Fallbacks
    log_dir = os.getenv("LOG_DIR", "/var/log/silvasonic")
    try:
        os.makedirs(log_dir, exist_ok=True)
        # Check if writable
        if not os.access(log_dir, os.W_OK):
            raise PermissionError(f"{log_dir} is not writable")
    except (PermissionError, OSError):
        log_dir = os.path.join(os.getcwd(), ".logs")
        os.makedirs(log_dir, exist_ok=True)

    # JSON Formatter for stdlib handlers
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
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    # File
    log_file = os.path.join(log_dir, "dashboard.log")
    try:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except Exception as e:
        print(f"Failed to setup file logging: {e}")

    # Configure Basic Config
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)

    # Reduce noise from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
