import json
import logging
import os
import queue
import socket
import threading
import time

import psutil
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
                    self.file_queue.task_done()

            except Exception as e:
                logger.error(f"Worker thread error: {e}")
                time.sleep(1)

    def write_status(self, status: str, error: Exception | str | None = None) -> None:
        if error:
            self._last_error = str(error)
            self._last_error_time = time.time()
        try:
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
                },
                "last_error": self._last_error,
                "last_error_time": self._last_error_time,
                "pid": os.getpid(),
            }

            hostname = socket.gethostname()
            status_file = f"/mnt/data/services/silvasonic/status/birdnet_{hostname}.json"
            os.makedirs(os.path.dirname(status_file), exist_ok=True)

            tmp_file = f"{status_file}.tmp"
            with open(tmp_file, "w") as f:
                json.dump(data, f)
            os.rename(tmp_file, status_file)
        except Exception as e:
            logger.error(f"Failed to write status: {e}")

    def scan_existing(self) -> None:
        self.write_status("Scanning")
        if not config.INPUT_DIR.exists():
            return
        # MVP: Skip deep scan for now to avoid CPU storm on restart
        # Logic: If we enable this, we should iterate file and put to queue
        pass
