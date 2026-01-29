import logging
import os
import shutil
import threading
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from silvasonic_processor.db import Recording, get_session

logger = logging.getLogger(__name__)


class Janitor(threading.Thread):
    def __init__(self, shutdown_event: threading.Event) -> None:
        super().__init__(name="Janitor")
        self.shutdown_event = shutdown_event
        self.interval = 300  # 5 minutes
        self.data_dir = "/data/recordings"
        self.warn_percent = int(os.getenv("DISK_THRESHOLD_WARNING", 80))
        self.crit_percent = int(os.getenv("DISK_THRESHOLD_CRITICAL", 90))

    def run(self) -> None:
        logger.info("Janitor started.")
        while not self.shutdown_event.is_set():
            try:
                self.cleanup()
            except Exception as e:
                logger.error(f"Janitor loop error: {e}", exc_info=True)

            # Sleep with check
            for _ in range(self.interval):
                if self.shutdown_event.is_set():
                    break
                time.sleep(1)

    def cleanup(self) -> None:
        # Check disk usage
        total, used, free = shutil.disk_usage(self.data_dir)
        usage_percent = (used / total) * 100
        logger.info(
            f"Disk Usage: {usage_percent:.1f}% (Warn: {self.warn_percent}%, Crit: {self.crit_percent}%)"
        )

        if usage_percent < self.warn_percent:
            return

        session = get_session()
        try:
            # Strategies
            if usage_percent > self.crit_percent:
                logger.warning("Disk usage CRITICAL. Deleting oldest files indiscriminately!")
                # Delete oldest, regardless of status
                self.delete_recursive(session, limit=10, force=True)
            elif usage_percent > self.warn_percent:
                logger.info("Disk usage WARNING. Deleting uploaded/analyzed files.")
                # Delete uploaded AND analyzed files
                self.delete_recursive(session, limit=10, force=False)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Cleanup failed: {e}")
        finally:
            session.close()

    def delete_recursive(self, session: Session, limit: int, force: bool) -> None:
        # Find candidates
        stmt = select(Recording).order_by(Recording.time.asc()).limit(limit)

        if not force:
            # Safe delete: Only uploaded and analyzed
            # Note: concept says "uploaded=true AND analyzed_bird=true"
            stmt = stmt.where(Recording.uploaded, Recording.analyzed_bird)

        candidates = session.execute(stmt).scalars().all()

        if not candidates and not force:
            logger.warning("No safe candidates found for deletion, but disk is full!")
            # Should we escalation to force? Concept says "Red <10% free -> Query DB for uploaded=true".
            # My logic is > Warning (which implies <20% free).
            return

        deleted_count = 0
        for rec in candidates:
            # Delete files
            self.delete_file(rec.path_high)
            self.delete_file(rec.path_low)

            # Delete thumbnail
            if rec.path_high:
                png = rec.path_high.replace(".wav", ".png")
                self.delete_file(png)

            # Remove from DB or mark as deleted?
            # Concept says "Janitor... deletes...". Usually implies removing the file.
            # If we remove the row, we lose history.
            # If we keep the row, we should set paths to NULL to indicate file is gone.

            # But the concept for "Janitor Logic (Detailed)" says: "DELETE oldest recording regardless of status".
            # And SQL example: `DELETE FROM recordings WHERE ...`
            # So we DELETE the row.

            session.delete(rec)
            deleted_count += 1

        logger.info(f"Janitor deleted {deleted_count} recordings.")

    def delete_file(self, path: str | None) -> None:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.debug(f"Deleted {path}")
            except Exception as e:
                logger.error(f"Failed to delete {path}: {e}")
