import time
import logging
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.config import config
from src.core.pipeline import AnalysisPipeline

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
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def scan_existing(self):
        if not config.INPUT_DIR.exists():
            return
            
        pattern = "**/*.flac" if config.RECURSIVE_WATCH else "*.flac"
        # Using pathlib for simpler globbing
        for file_path in config.INPUT_DIR.rglob("*.flac") if config.RECURSIVE_WATCH else config.INPUT_DIR.glob("*.flac"):
            self.pipeline.process_file(str(file_path))
