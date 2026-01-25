import sys
import os
import datetime
import logging
import subprocess
import csv
from pathlib import Path

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
logger = logging.getLogger("TestRunner")

# Import BirdNET-Analyzer
try:
    import birdnet_analyzer.analyze as bn_analyze
except ImportError as e:
    logger.error(f"CRITICAL: Could not import birdnet_analyzer: {e}")
    sys.exit(1)

def run_ffmpeg_resampling(input_path: Path, output_path: Path):
    """Resample to 48kHz mono using ffmpeg (robust against formats)"""
    try:
        cmd = [
            "ffmpeg", "-y", 
            "-i", str(input_path.absolute()), 
            "-ar", "48000", 
            "-ac", "1", 
            "-c:a", "pcm_s16le",
            str(output_path)
        ]
        # Suppress output unless error
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed for {input_path.name}: {e}")
        return False

def analyze_file(input_path: Path, results_dir: Path):
    """Process a single file using BirdNET-Analyzer"""
    logger.info(f"Processing: {input_path.name}")
    
    # Setup temp paths
    temp_dir = Path("/tmp/birdnet_processing")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_resampled = temp_dir / f"{input_path.stem}_48k.wav"
    
    # 1. Resample
    if not run_ffmpeg_resampling(input_path, temp_resampled):
        return

    # 2. Run BirdNET Analysis
    # We configure it to output to a temp directory first
    temp_output_dir = temp_dir / "results"
    temp_output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f"Running analysis on {temp_resampled.name}...")
        bn_analyze(
            audio_input=str(temp_resampled),
            min_conf=0.7, # User requested min 70% confidence
            lat=53.5, lon=10.0, week=-1, # Northern Germany (Hamburg area), Year-round filter
            overlap=0.0,
            sensitivity=1.0,
            threads=max(1, os.cpu_count() - 1),
            sf_thresh=0.0001,
            output=str(temp_output_dir),
            rtype='csv'
        )
    except Exception as e:
        logger.error(f"BirdNET analysis crashed: {e}")
        return

    # 3. Locate and Move/Rename Result File
    # BirdNET v2.4+ creates <filename>.BirdNET.results.csv
    expected_result_name = f"{temp_resampled.stem}.BirdNET.results.csv"
    temp_result_path = temp_output_dir / expected_result_name
    
    if not temp_result_path.exists():
        logger.warning(f"No result file found at {temp_result_path}. Input might be silent or too short.")
        # Debug listing
        try:
            logger.info(f"Contents of {temp_output_dir}: {[p.name for p in temp_output_dir.iterdir()]}")
        except: pass
        return

    # Move to final destination with clean name
    final_output_file = results_dir / f"{input_path.name}.csv"
    
    try:
        # We read the BirdNET CSV and write a cleaner one to final dir, 
        # or just copy it. Let's strictly move it to match user request.
        # But maybe we want to keep the content format identical?
        # User said: "Ergebnisse einfach als csv in /results!"
        
        # Let's just move/rename it.
        # However, the BirdNET CSV has columns: Start (s), End (s), Scientific name, Common name, Confidence
        # We might want to ensure the target directory exists.
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # We simply move the generated CSV to the final output path
        import shutil
        shutil.move(str(temp_result_path), str(final_output_file))
        logger.info(f"Saved results to: {final_output_file}")
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")

    # Cleanup temp audio
    try:
        if temp_resampled.exists():
            temp_resampled.unlink()
    except: pass

def main():
    logger.info("--- Starting Standalone BirdNET Test Runner ---")
    
    # Define directories
    input_dir = Path("/app/test_data")
    results_dir = Path("/data/db/results") # Mapped to local ./results in run_test.sh
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)
        
    # Find files
    files = list(input_dir.glob("*.flac")) + list(input_dir.glob("*.wav"))
    logger.info(f"Found {len(files)} audio files.")
    
    if not files:
        logger.warning(f"No .flac or .wav files found in {input_dir}")
        return

    # Process
    for f in files:
        analyze_file(f, results_dir)
        
    logger.info("--- All done ---")

if __name__ == "__main__":
    main()
