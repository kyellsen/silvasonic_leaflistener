import logging
import shutil
import subprocess
import typing
from pathlib import Path

import soundfile as sf

try:
    import birdnet_analyzer.analyze as bn_analyze
except ImportError:
    bn_analyze = None

from silvasonic_birdnet.config import config
from silvasonic_birdnet.database import db

logger = logging.getLogger("Analyzer")


class BirdNETAnalyzer:
    def __init__(self) -> None:
        logger.info("Initializing BirdNET Analyzer (Simple Mode)...")
        if bn_analyze is None:
            logger.error("BirdNET-Analyzer module not found!")

        # Ensure results dir exists
        config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize Database
        logger.info("Connecting to Database...")
        db.connect()

    def process_file(self, file_path: str) -> None:
        """Analyze a single audio file and save CSV results."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return

        logger.info(f"Processing: {path.name}")

        # Setup temp paths
        start_time_epoch = __import__("time").time()
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

            # Sanitize location (pass None if disabled/default -1)
            lat = settings["lat"]
            lon = settings["lon"]
            if lat == -1 or lon == -1:
                lat = None
                lon = None

            if bn_analyze:
                bn_analyze(
                    audio_input=str(temp_resampled),
                    min_conf=settings["min_conf"],
                    lat=lat,
                    lon=lon,
                    week=settings["week"],
                    overlap=settings["overlap"],
                    sensitivity=settings["sensitivity"],
                    threads=settings["threads"],
                    sf_thresh=0.0001,
                    output=str(temp_output_dir),
                    rtype="csv",
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

                    with open(final_output_file, encoding="utf-8") as f:
                        reader = csv.reader(f)
                        next(reader, None)  # Skip header usage

                        for row in reader:
                            detection_count += 1
                            if len(row) < 5:
                                continue

                            # Parse Row: Start (s), End (s), Scientific name, Common name, Confidence
                            try:
                                start_t = float(row[0])
                                end_t = float(row[1])
                                conf = float(row[4])
                                common_name = row[3]

                                # Save Clip
                                clip_path = self._save_clip(
                                    temp_resampled, start_t, end_t, common_name
                                )

                                detection = {
                                    "filename": path.name,
                                    "filepath": str(path),
                                    "start_time": start_t,
                                    "end_time": end_t,
                                    "scientific_name": row[2],
                                    "common_name": common_name,
                                    "confidence": conf,
                                    "lat": config.LATITUDE,
                                    "lon": config.LONGITUDE,
                                    "clip_path": clip_path,
                                    "source_device": path.parent.name,  # Extract source from folder (e.g. "front_mic")
                                }
                                db.save_detection(detection)

                                # Check Watchlist & Alert
                                if db.is_watched(row[2]):
                                    self._trigger_alert(detection)

                            except ValueError:
                                logger.warning(f"Skipping invalid row in {final_output_file}")

                    if detection_count == 0:
                        logger.warning(f"Analysis produced 0 detections for {path.name}.")
                    else:
                        logger.info(
                            f"Analysis finished for {path.name}: Found {detection_count} detections. Saved to DB."
                        )

                except Exception as e:
                    logger.error(f"Failed to read result file for verification/DB: {e}")

            except Exception as e:
                logger.error(f"Failed to save results: {e}")
        else:
            logger.warning("No result file found. Input might be silent or too short.")

        # Log Processing Stats (Always, even if no detections or silent)
        try:
            # Estimate audio duration from file or use a standard (30s)
            # Better to read from audio metadata if possible, but SF read is slow.
            # Assuming chunks are 30s as per recorder config, or use soundfile info.
            try:
                info = sf.info(str(path))
                duration = info.duration
            except Exception:
                duration = 10.0  # Fallback

            import time

            processing_time = time.time() - start_time_epoch
            db.log_processed_file(path.name, duration, processing_time)
        except Exception as e:
            logger.error(f"Failed to log processing stats: {e}")

        # Cleanup
        try:
            if temp_resampled.exists():
                temp_resampled.unlink()
        except Exception:
            pass

    def _save_clip(self, audio_path: Path, start_time: float, end_time: float, species: str) -> str:
        """Extracts and saves the audio clip for a detection.
        Returns the relative path to the clip or None if failed.
        """
        try:
            # Create clips directory if it doesn't exist
            config.CLIPS_DIR.mkdir(parents=True, exist_ok=True)

            # Generate filename: {original_name}_{start}_{end}_{species}.wav
            # Sanitize species name for filename
            safe_species = (
                "".join([c for c in species if c.isalnum() or c in (" ", "_")])
                .strip()
                .replace(" ", "_")
            )
            clip_name = f"{audio_path.stem}_{start_time:.1f}_{end_time:.1f}_{safe_species}.wav"
            clip_path = config.CLIPS_DIR / clip_name

            # Read the specific segment with padding
            # We use soundfile for precision reading
            # Note: start/end are in seconds
            PADDING = 3.0
            clip_start = max(0.0, start_time - PADDING)
            clip_end = end_time + PADDING

            data, samplerate = sf.read(
                str(audio_path),
                start=int(clip_start * 48000),
                stop=int(clip_end * 48000),
                always_2d=True,
            )

            sf.write(str(clip_path), data, samplerate)

            # Return path relative to RESULTS_DIR for portability if needed, or just absolute string
            # Returning absolute path as string for now to match DB schema
            return str(clip_path)

        except Exception as e:
            logger.error(f"Failed to save clip for {audio_path.name}: {e}")
            return ""

    def _run_ffmpeg_resampling(self, input_path: Path, output_path: Path) -> bool:
        """Resample to 48kHz mono using ffmpeg (robust against formats)"""
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path.absolute()),
                "-ar",
                "48000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ]
            # Suppress output unless error
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed for {input_path.name}: {e}")
            return False
            logger.error(f"Resampling error: {e}")
            return False

    def _trigger_alert(self, detection: dict[str, typing.Any]) -> None:
        """Creates a notification event in the shared queue."""
        try:
            # Shared notification queue path
            # Using /data/notifications (mapped volume)
            queue_dir = Path("/data/notifications")
            queue_dir.mkdir(parents=True, exist_ok=True)

            import json
            import time

            event_id = f"{int(time.time() * 1000)}_{detection['scientific_name'].replace(' ', '_')}"
            event_path = queue_dir / f"{event_id}.json"

            payload = {"type": "bird_detection", "timestamp": time.time(), "data": detection}

            with open(event_path, "w") as f:
                json.dump(payload, f)

            logger.info(f"Triggered notification alert for {detection['common_name']}")

        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
