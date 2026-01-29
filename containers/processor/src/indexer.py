import json
import logging
import os
import threading
import time
from datetime import UTC, datetime

import redis
import soundfile as sf
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.db import Recording, get_session
from src.thumbnailer import Thumbnailer

logger = logging.getLogger(__name__)


class Indexer(threading.Thread):
    def __init__(self, shutdown_event):
        super().__init__(name="Indexer")
        self.shutdown_event = shutdown_event
        self.scan_interval = int(os.getenv("SCAN_INTERVAL", 10))
        self.root_dir = "/data/recordings"
        self.thumbnailer = Thumbnailer()
        self.redis_host = os.getenv("REDIS_HOST", "silvasonic_redis")
        self.redis_client = None

    def get_redis(self):
        if not self.redis_client:
            try:
                self.redis_client = redis.Redis(host=self.redis_host, port=6379, db=0)
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
        return self.redis_client

    def run(self):
        logger.info("Indexer started.")
        while not self.shutdown_event.is_set():
            try:
                self.scan()
            except Exception as e:
                logger.error(f"Indexer loop error: {e}", exc_info=True)

            # Sleep with check
            for _ in range(self.scan_interval):
                if self.shutdown_event.is_set():
                    break
                time.sleep(1)

    def scan(self):
        session = get_session()
        try:
            # Walk through device directories
            if not os.path.exists(self.root_dir):
                logger.warning(f"Root dir {self.root_dir} does not exist yet.")
                return

            for device_id in os.listdir(self.root_dir):
                device_path = os.path.join(self.root_dir, device_id)
                if not os.path.isdir(device_path):
                    continue

                # Check high_res and low_res folders
                high_res_path = os.path.join(device_path, "high_res")
                low_res_path = os.path.join(device_path, "low_res")

                # We focus on high_res as the primary source of truth for "new recording"
                if os.path.exists(high_res_path):
                    self.process_directory(session, device_id, high_res_path, is_high_res=True)

                # We also check low_res to update paths if needed (though high_res should drive creation)
                if os.path.exists(low_res_path):
                    self.process_directory(session, device_id, low_res_path, is_high_res=False)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Scan failed: {e}")
        finally:
            session.close()

    def process_directory(self, session: Session, device_id: str, dir_path: str, is_high_res: bool):
        for filename in os.listdir(dir_path):
            if not filename.endswith(".wav"):
                continue

            filepath = os.path.join(dir_path, filename)

            # Identify recording by filename/device
            # We assume filename is unique enough or contains timestamp

            # Check if exists in DB
            stmt = select(Recording).where(
                (Recording.path_high == filepath)
                if is_high_res
                else (Recording.path_low == filepath)
            )
            recording = session.execute(stmt).scalar_one_or_none()

            if recording:
                # Already indexed loop
                continue

            # If not found by exact path, try to find by filename partner
            # e.g. if we found low_res, check if high_res entry exists
            # This logic depends on filename matching.
            # If we don't have a partner, we create a new record.

            # To avoid duplicates if we scan low_res first, we try to match by filename properties or partner path
            # Assuming filename structure is consistent.

            partner_path = (
                filepath.replace("high_res", "low_res")
                if is_high_res
                else filepath.replace("low_res", "high_res")
            )

            stmt = select(Recording).where(
                (Recording.path_low == partner_path)
                if is_high_res
                else (Recording.path_high == partner_path)
            )
            recording = session.execute(stmt).scalar_one_or_none()

            if recording:
                # Update existing record
                if is_high_res:
                    recording.path_high = filepath
                else:
                    recording.path_low = filepath
                logger.info(
                    f"Updated recording {recording.id} with {'high' if is_high_res else 'low'} path"
                )
            else:
                # New record
                # Get metadata
                try:
                    info = sf.info(filepath)
                    duration = info.duration
                    samplerate = info.samplerate
                except Exception as e:
                    logger.error(f"Failed to read audio info for {filepath}: {e}")
                    duration = 0
                    samplerate = 0

                # Parse timestamp from filename or metadata?
                # Filename usually: YYYYMMDD_HHMMSS.wav or similar.
                # Use file mtime if parse fails, or just now()
                # Ideally recorder writes UTC timestamp in filename

                timestamp = datetime.now(UTC)
                # Try to parse filename: 20231024_120000.wav
                try:
                    _ = os.path.splitext(filename)[0]
                    # Adjust format as per Recorder's output
                    # Assuming basic format for now, fallback to mtime
                    timestamp = datetime.fromtimestamp(os.path.getmtime(filepath), UTC)
                except Exception:
                    pass

                recording = Recording(
                    time=timestamp,
                    path_high=filepath if is_high_res else None,
                    path_low=filepath if not is_high_res else None,
                    device_id=device_id,
                    duration_sec=duration,
                    samplerate_hz=samplerate,
                )
                session.add(recording)
                session.flush()  # Get ID
                logger.info(f"Indexed new recording: {filename} (ID: {recording.id})")

                # Publish event
                r = self.get_redis()
                if r:
                    try:
                        r.publish(
                            "alerts",
                            json.dumps(
                                {
                                    "type": "info",
                                    "title": "New Recording",
                                    "body": f"New file from {device_id}",
                                    "tag": "#recording",
                                }
                            ),
                        )
                    except Exception:
                        pass

            # Actions after indexing (or seeing it again)
            if is_high_res and not recording.analyzed_bat:
                # Check if thumb exists
                png_path = filepath.replace(".wav", ".png")
                if not os.path.exists(png_path):
                    logger.info(f"Generating thumbnail for {filepath}")
                    self.thumbnailer.generate(filepath)
                    # Note: we don't store PNG path in DB, it's implicit
