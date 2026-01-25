import sys
import os
import logging
from pathlib import Path
from unittest.mock import MagicMock

# --- MOCKING LAYER ---
# We must mock src.database BEFORE importing src.analyzer
print("Setting up Mock Database Layer...")
mock_db = MagicMock()
sys.modules['src.database'] = mock_db

# Mock SessionLocal and Detection
mock_session = MagicMock()
mock_db.SessionLocal.return_value = mock_session
mock_db.Detection = MagicMock()

# Ensure config doesn't break if we import it
# (Config is robust, but let's be safe)

# --- IMPORTS ---
try:
    from src.analyzer import BirdNETAnalyzer
    from src.config import config
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import BirdNETAnalyzer: {e}")
    sys.exit(1)

# --- SETUP LOGGING ---
# Reconfigure logging to be very verbose
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger("TestRunner")

def main():
    logger.info("Starting BirdNET Test Runner...")
    
    test_data_dir = Path("/app/test_data")
    if not test_data_dir.exists():
        logger.error(f"Test data directory not found: {test_data_dir}")
        logger.error("Please mount valid .flac files to /app/test_data")
        sys.exit(1)
        
    files = list(test_data_dir.glob("*.flac")) + list(test_data_dir.glob("*.wav"))
    
    if not files:
        logger.warning(f"No .flac or .wav files found in {test_data_dir}")
        sys.exit(0)
    
    logger.info(f"Found {len(files)} files to process.")
    
    # Initialize Analyzer
    analyzer = BirdNETAnalyzer()
    
    # Process each file
    for audio_file in files:
        logger.info(f"--- Processing {audio_file.name} ---")
        try:
            analyzer.process_file(str(audio_file))
        except Exception as e:
            logger.error(f"Failed to process {audio_file.name}: {e}", exc_info=True)
            
    logger.info("All files processed.")
    logger.info("Check /data/db/results for CSV outputs.")

if __name__ == "__main__":
    main()
