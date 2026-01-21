
import sys
import os
from pathlib import Path
import logging

# Ensure src is in path
sys.path.append(str(Path(__file__).parent.parent))

from src.analyzer import BirdNETAnalyzer
from src.config import config

# Mock configs for verification
def verify():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Verification")

    # 1. Check Config Defaults
    logger.info(f"Config Check: LOCATION_FILTER_ENABLED = {config.LOCATION_FILTER_ENABLED}")
    logger.info(f"Config Check: LATITUDE = {config.LATITUDE}")
    logger.info(f"Config Check: SIG_OVERLAP = {config.SIG_OVERLAP}")

    # 2. Instantiate Analyzer
    analyzer = BirdNETAnalyzer()
    
    # 3. Dummy File Check
    # We need a valid audio file to really test BirdNET. 
    # If we don't have one, we can't fully certify the fix without a mocked bn_analyze, 
    # but the goal here is to verify the LOGIC flow respects the config.
    
    # Let's check if we can simulate the "process_file" call logic
    # We will inspect the log output manually to see if "Lat=None" was passed when Filter=False.
    
    logger.info("Verification script loaded. Please run this in an environment where 'src' is importable.")
    logger.info("If you have an audio file, pass it as an argument.")

    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        if os.path.exists(audio_file):
            logger.info(f"Testing analysis on {audio_file}")
            analyzer.process_file(audio_file)
        else:
            logger.error(f"File {audio_file} not found.")

if __name__ == "__main__":
    verify()
