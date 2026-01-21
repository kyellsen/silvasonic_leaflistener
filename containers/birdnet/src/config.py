import os
from pathlib import Path

class Config:
    # Paths
    INPUT_DIR = Path(os.getenv("INPUT_DIR", "/data/recording"))
    DB_PATH = Path(os.getenv("DB_PATH", "/data/db/birdnet.sqlite"))
    
    # Watcher
    RECURSIVE_WATCH = os.getenv("RECURSIVE_WATCH", "true").lower() == "true"
    
    # BirdNET Settings
    # Location for species prediction (optional)
    # If None, no location filter is applied (= global species list)
    _lat = os.getenv("LATITUDE")
    LATITUDE = float(_lat) if _lat else None
    
    _lon = os.getenv("LONGITUDE")
    LONGITUDE = float(_lon) if _lon else None
    
    # Minimum confidence to store a detection (0.0 - 1.0)
    MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.7"))
    
    # Analysis chunks
    SIG_LENGTH = 3.0  # BirdNET standard is 3 seconds
    SIG_OVERLAP = 0.0 # No overlap for raw speed, can be increased if needed
    
    # Threads - BirdNET Analyzer can use multi-threading
    THREADS = int(os.getenv("THREADS", "1"))

config = Config()
