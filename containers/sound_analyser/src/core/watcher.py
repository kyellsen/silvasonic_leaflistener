import logging
import time

from src.config import config
from src.core.pipeline import AnalysisPipeline
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger("Watcher")

class AudioFileHandler(FileSystemEventHandler):
    def __init__(self, pipeline: AnalysisPipeline):
        self.pipeline = pipeline

    def on_closed(self, event):
        # We listen for close_write events to ensure file is fully written
        if event.is_directory:
            return
        if not event.src_path.endswith('.flac'):
            return

        logger.info(f"File closed event detected: {event.src_path}")
        # Standardize path if needed (Wait a tiny bit to ensure lock release?)
        self.pipeline.process_file(event.src_path)

class WatcherService:
    def __init__(self):
        self.pipeline = AnalysisPipeline()
        self.observer = Observer()

    def run(self):
        # Scan existing files first
        logger.info("Scanning existing files...")
        self.scan_existing()

        # Start Watcher
        logger.info(f"Starting Watchdog on {config.INPUT_DIR} (Recursive: {config.RECURSIVE_WATCH})")
        event_handler = AudioFileHandler(self.pipeline)

        # Ensure input dir exists, otherwise wait
        while not config.INPUT_DIR.exists():
            logger.warning(f"Input dir {config.INPUT_DIR} not found, waiting...")
            time.sleep(5)

        self.observer.schedule(event_handler, str(config.INPUT_DIR), recursive=config.RECURSIVE_WATCH)
        self.observer.start()

        try:
            while True:
                self.write_status("Idle (Watching)")
                time.sleep(10)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def write_status(self, status: str):
        try:
            import json
            import os

            import psutil

            data = {
                "service": "sound_analyser",
                "timestamp": time.time(),
                "status": status,
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "meta": {
                    "input_dir": str(config.INPUT_DIR)
                },
                "pid": os.getpid()
            }

            status_file = "/mnt/data/services/silvasonic/status/sound_analyser.json"
            os.makedirs(os.path.dirname(status_file), exist_ok=True)

            tmp_file = f"{status_file}.tmp"
            with open(tmp_file, 'w') as f:
                json.dump(data, f)
            os.rename(tmp_file, status_file)
        except Exception as e:
            logger.error(f"Failed to write status: {e}")

    def scan_existing(self):
        self.write_status("Scanning")
        if not config.INPUT_DIR.exists():
            return

        pattern = "**/*.flac" if config.RECURSIVE_WATCH else "*.flac"
        # Using pathlib for simpler globbing
        for file_path in config.INPUT_DIR.rglob("*.flac") if config.RECURSIVE_WATCH else config.INPUT_DIR.glob("*.flac"):
            self.pipeline.process_file(str(file_path))
