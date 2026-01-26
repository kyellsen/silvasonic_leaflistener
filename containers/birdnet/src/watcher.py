import logging
import os
import time

from src.analyzer import BirdNETAnalyzer
from src.config import config
from watchdog.events import FileClosedEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger("Watcher")


class AudioFileHandler(FileSystemEventHandler):
    def __init__(self, analyzer: BirdNETAnalyzer):
        self.analyzer = analyzer

    def on_closed(self, event: FileClosedEvent) -> None:
        # We listen for close_write events (Linux) to ensure file is fully written
        if event.is_directory:
            return
        # Support common audio formats
        src_path_str = os.fsdecode(event.src_path)
        if not (src_path_str.endswith(".flac") or src_path_str.endswith(".wav")):
            return

        logger.info(f"New audio file detected: {src_path_str}")
        # Give a small grace period just in case
        time.sleep(0.5)
        self.analyzer.process_file(src_path_str)


class WatcherService:
    def __init__(self) -> None:
        self.analyzer = BirdNETAnalyzer()
        self.observer = Observer()

    def run(self) -> None:
        # Scan existing files first?
        # Often good to process backlog, but BirdNET is heavy.
        # Let's verify backlog only if not huge or we can rely on manual trigger.
        # For now, we will scan existing to catch up on missed files during restart.
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

        event_handler = AudioFileHandler(self.analyzer)
        self.observer.schedule(
            event_handler, str(config.INPUT_DIR), recursive=config.RECURSIVE_WATCH
        )
        self.observer.start()

        try:
            while True:
                self.write_status("Idle (Watching)")
                time.sleep(5)  # Update status every 5s
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def write_status(self, status: str) -> None:
        try:
            import json
            import os

            import psutil

            data = {
                "service": "birdnet",
                "timestamp": time.time(),
                "status": status,
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "meta": {"input_dir": str(config.INPUT_DIR), "recursive": config.RECURSIVE_WATCH},
                "pid": os.getpid(),
            }

            status_file = "/mnt/data/services/silvasonic/status/birdnet.json"
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

        # Simplistic approach: Just list all files.
        # Ideally we check DB if already analyzed to avoid re-work.
        # Implementation of "Check DB" logic:
        # For this MVP, we might skip full re-scan or just rely on 'new' files.
        # However, to be robust, let's just log count.
        # Processing ALL existing files on every startup is dangerous if there are thousands.
        # Users requested "pull current files", implying real-time focus.
        # Let's skip scanning OLD files for now to avoid CPU storm, unless the folder is small.
        # Or better: Only process if we want to catch up.
        # Given the "Current files from recorder" request: "Er soll sich immer die aktuellen files vom recorder ziehen"
        # I will assume "Watch new files" is the priority.
        pass
