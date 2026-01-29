import signal
import sys
import threading
import time

import structlog

from silvasonic_birdnet.analyzer import BirdNETAnalyzer
from silvasonic_birdnet.database import db

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
shutdown_event = threading.Event()


def signal_handler(signum, frame):
    logger.info("Shutdown signal received")
    shutdown_event.set()


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Silvasonic BirdNET (V2 DB Polling)...")

    # Connect DB
    if not db.connect():
        logger.error("Failed to connect to DB. Exiting.")
        sys.exit(1)

    analyzer = BirdNETAnalyzer()

    logger.info("Entering Analysis Loop...")

    while not shutdown_event.is_set():
        try:
            pending = db.get_pending_analysis(limit=1)

            if not pending:
                time.sleep(5)
                continue

            rec = pending[0]
            rec_id = rec["id"]
            # Prefer Low Res (48k)
            path = rec.get("path_low") or rec.get("path_high")

            if not path:
                logger.warning(f"Recording {rec_id} has no valid paths. Skipping.", id=rec_id)
                db.mark_analyzed(rec_id)
                continue

            logger.info(f"Analyzing Recording {rec_id}: {path}")

            # Analyze
            analyzer.process_file(path)

            # Mark Done
            db.mark_analyzed(rec_id)

        except Exception:
            logger.exception("Analysis Loop Error")
            time.sleep(5)

    logger.info("BirdNET Service Shutdown.")


if __name__ == "__main__":
    main()
