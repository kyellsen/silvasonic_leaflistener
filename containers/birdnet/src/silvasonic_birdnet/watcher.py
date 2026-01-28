import json
import logging
import os
import queue
import socket
import threading
import time

import psutil
import redis
from watchdog.events import FileClosedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from silvasonic_birdnet.analyzer import BirdNETAnalyzer
from silvasonic_birdnet.config import config

logger = logging.getLogger("Watcher")


class AudioFileHandler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, file_queue: "queue.Queue[str]"):
        self.file_queue = file_queue

    def on_closed(self, event: FileClosedEvent) -> None:
        # We listen for close_write events (Linux) to ensure file is fully written
        if event.is_directory:
            return
        # Support common audio formats
        src_path_str = os.fsdecode(event.src_path)
        if not (src_path_str.endswith(".flac") or src_path_str.endswith(".wav")):
            return

        logger.info(f"New audio file detected: {src_path_str}")
        self.file_queue.put(src_path_str)


class WatcherService:
    def __init__(self) -> None:
        self.analyzer = BirdNETAnalyzer()
        self.observer = Observer()
        self.file_queue: queue.Queue[str] = queue.Queue()
        self.is_processing = False
        self._current_file: str | None = None
        self._current_file_start_time: float | None = None
        self._last_error: str | None = None
        self._last_error_time: float | None = None
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

    def run(self) -> None:
        logger.info("Scanning existing files...")
        self.scan_existing()

        # Start Watcher
        logger.info(
            f"Starting Watchdog on {config.INPUT_DIR} (Recursive: {config.RECURSIVE_WATCH})"
        )

        # Ensure input dir exists
        while not config.INPUT_DIR.exists():
            logger.warning(f"Input dir {config.INPUT_DIR} not found, waiting...")
            time.sleep(5)

        event_handler = AudioFileHandler(self.file_queue)
        self.observer.schedule(
            event_handler, str(config.INPUT_DIR), recursive=config.RECURSIVE_WATCH
        )
        self.observer.start()

        # Start Worker Thread
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

        try:
            while True:
                status = "Processing" if self.is_processing else "Idle (Watching)"
                self.write_status(status)
                time.sleep(5)  # Update status every 5s
        except KeyboardInterrupt:
            logger.info("Stopping...")
            self._stop_event.set()
            self.observer.stop()
        except Exception as e:
            logger.error(f"Watcher crashed: {e}")
            self.write_status("Error: Crashed", error=e)
            self._stop_event.set()
            self.observer.stop()

        # Wait for loose ends (optional, mostly for clean join)
        self.observer.join()
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)

    def _worker(self) -> None:
        """Background thread to process files from the queue."""
        logger.info("Worker thread started.")
        while not self._stop_event.is_set():
            try:
                # Check for files
                try:
                    # Timeout allows checking stop_event periodically
                    file_path = self.file_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                self.is_processing = True
                self._current_file = os.path.basename(file_path)
                self._current_file_start_time = time.time()

                # Update status immediately to show "Processing..."
                self.write_status("Processing")

                try:
                    # Give a small grace period (logic moved from Handler, but fine here too)
                    time.sleep(0.5)
                    self.analyzer.process_file(file_path)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    self._last_error = str(e)
                    self._last_error_time = time.time()
                finally:
                    self.is_processing = False
                    self._current_file = None
                    self._current_file_start_time = None
                    self.file_queue.task_done()
                    # Update status immediately to return to Idle
                    self.write_status("Idle (Watching)")

            except Exception as e:
                logger.error(f"Worker thread error: {e}")
                time.sleep(1)

    def write_status(self, status: str, error: Exception | str | None = None) -> None:
        if error:
            self._last_error = str(error)
            self._last_error_time = time.time()

        processing_duration = 0.0
        if self._current_file_start_time and self.is_processing:
            processing_duration = time.time() - self._current_file_start_time

        try:
            if not hasattr(self, "_redis"):
                self._redis = redis.Redis(
                    host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=1
                )

            data = {
                "service": "birdnet",
                "timestamp": time.time(),
                "status": status,
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "meta": {
                    "input_dir": str(config.INPUT_DIR),
                    "recursive": config.RECURSIVE_WATCH,
                    "queue_size": self.file_queue.qsize(),
                    "current_file": self._current_file,
                    "processing_duration_sec": round(processing_duration, 2)
                    if self.is_processing
                    else None,
                },
                "last_error": self._last_error,
                "last_error_time": self._last_error_time,
                "pid": os.getpid(),
            }

            hostname = socket.gethostname()
            # Key: status:birdnet:<hostname>
            key = f"status:birdnet:{hostname}"

            # 10s TTL
            self._redis.setex(key, 10, json.dumps(data))

        except Exception as e:
            logger.error(f"Failed to write status to Redis: {e}")

    def scan_existing(self) -> None:
        self.write_status("Scanning")
        if not config.INPUT_DIR.exists():
            return
        # MVP: Skip deep scan for now to avoid CPU storm on restart
        # Logic: If we enable this, we should iterate file and put to queue
        pass
