import os
import shutil
import logging
import subprocess
from pathlib import Path
import soundfile as sf

try:
    import birdnet_analyzer.analyze as bn_analyze
except ImportError:
    bn_analyze = None

from src.config import config

logger = logging.getLogger("Analyzer")

class BirdNETAnalyzer:
    def __init__(self):
        logger.info("Initializing BirdNET Analyzer (Simple Mode)...")
        if bn_analyze is None:
            logger.error("BirdNET-Analyzer module not found!")
            
        # Ensure results dir exists
        config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def process_file(self, file_path: str):
        """
        Analyze a single audio file and save CSV results.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return

        logger.info(f"Processing: {path.name}")
        
        # Setup temp paths
        temp_dir = Path("/tmp/birdnet_processing")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_resampled = temp_dir / f"{path.stem}_48k.wav"
        
        # 1. Resample (Robustness)
        if not self._run_ffmpeg_resampling(path, temp_resampled):
            return

        # 2. Run BirdNET Analysis
        temp_output_dir = temp_dir / "results"
        temp_output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Running analysis on {temp_resampled.name}...")
            if bn_analyze:
                bn_analyze(
                    audio_input=str(temp_resampled),
                    min_conf=config.MIN_CONFIDENCE,
                    lat=config.LATITUDE,
                    lon=config.LONGITUDE,
                    week=config.WEEK,
                    overlap=config.OVERLAP,
                    sensitivity=config.SENSITIVITY,
                    threads=config.THREADS,
                    sf_thresh=0.0001,
                    output=str(temp_output_dir),
                    rtype='csv'
                )
            else:
                logger.error("BirdNET Analyzer not loaded, skipping analysis.")
                return
                
        except Exception as e:
            logger.error(f"BirdNET analysis crashed: {e}")
            return

        # 3. Locate and Move/Rename Result File
        expected_result_name = f"{temp_resampled.stem}.BirdNET.results.csv"
        temp_result_path = temp_output_dir / expected_result_name
        
        final_output_file = config.RESULTS_DIR / f"{path.name}.csv"
        
        if temp_result_path.exists():
            # Move to final destination
            try:
                shutil.move(str(temp_result_path), str(final_output_file))
                logger.info(f"Saved results to: {final_output_file}")
                
                # Verify content if needed?
                # For now just log success.
                pass
            except Exception as e:
                logger.error(f"Failed to save results: {e}")
        else:
            logger.warning(f"No result file found. Input might be silent or too short.")

        # Cleanup
        try:
            if temp_resampled.exists():
                temp_resampled.unlink()
        except:
            pass

    def _run_ffmpeg_resampling(self, input_path: Path, output_path: Path):
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
        except Exception as e:
            logger.error(f"Resampling error: {e}")
            return False
