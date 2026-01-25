import os
from pathlib import Path

class Config:
    # Paths
    INPUT_DIR = Path(os.getenv("INPUT_DIR", "/data/recording"))
    RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "/data/db/results"))
    
    # Watcher
    RECURSIVE_WATCH = os.getenv("RECURSIVE_WATCH", "true").lower() == "true"
    
    # BirdNET Settings
    # Minimum confidence to store a detection (0.0 - 1.0)
    MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.7"))
    
    # Threads - BirdNET Analyzer can use multi-threading
    THREADS = int(os.getenv("THREADS", "1"))
    
    # Location (Optional - defaults to -1 for global if not set)
    # Using defaults similar to BirdNET-Pi or Global
    _lat = os.getenv("LATITUDE")
    LATITUDE = float(_lat) if _lat else -1
    
    _lon = os.getenv("LONGITUDE")
    LONGITUDE = float(_lon) if _lon else -1
    
    WEEK = int(os.getenv("WEEK", "-1"))
    OVERLAP = float(os.getenv("OVERLAP", "0.0"))
    SENSITIVITY = float(os.getenv("SENSITIVITY", "1.0"))


config = Config()
