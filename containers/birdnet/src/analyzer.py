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
from src.database import db

logger = logging.getLogger("Analyzer")

class BirdNETAnalyzer:
    def __init__(self):
        logger.info("Initializing BirdNET Analyzer (Simple Mode)...")
        if bn_analyze is None:
            logger.error("BirdNET-Analyzer module not found!")
            
        # Ensure results dir exists
        config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize Database
        logger.info("Connecting to Database...")
        db.connect()

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
            settings = config.birdnet_settings
            if bn_analyze:
                bn_analyze(
                    audio_input=str(temp_resampled),
                    min_conf=settings['min_conf'],
                    lat=settings['lat'],
                    lon=settings['lon'],
                    week=settings['week'],
                    overlap=settings['overlap'],
                    sensitivity=settings['sensitivity'],
                    threads=settings['threads'],
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
                
                # Verify content and log detection count
                try:
                    import csv
                    detection_count = 0
                    
                    with open(final_output_file, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        header = next(reader, None) # Skip header usage
                        
                        for row in reader:
                            detection_count += 1
                            if len(row) < 5: 
                                continue
                                
                            # Parse Row: Start (s), End (s), Scientific name, Common name, Confidence
                            try:
                                detection = {
                                    'filename': path.name,
                                    'filepath': str(path),
                                    'start_time': float(row[0]),
                                    'end_time': float(row[1]),
                                    'scientific_name': row[2],
                                    'common_name': row[3],
                                    'confidence': float(row[4]),
                                    'lat': config.LATITUDE,
                                    'lon': config.LONGITUDE
                                }
                                db.save_detection(detection)
                            except ValueError:
                                logger.warning(f"Skipping invalid row in {final_output_file}")

                    if detection_count == 0:
                        logger.warning(f"Analysis produced 0 detections for {path.name}.")
                    else:
                        logger.info(f"Analysis finished for {path.name}: Found {detection_count} detections. Saved to DB.")
                        
                except Exception as e:
                    logger.error(f"Failed to read result file for verification/DB: {e}")

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
