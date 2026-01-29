import csv
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import redis
import soundfile as sf

from silvasonic_birdnet.config import config
from silvasonic_birdnet.database import db
from silvasonic_birdnet.models import BirdDetection

try:
    import birdnet_analyzer.analyze as bn_analyze
except ImportError:
    bn_analyze = None


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

        # Parse Timestamp from Filename (CRITICAL for Data Integrity)
        file_start_time = self._parse_timestamp_from_filename(path.name)
        if file_start_time is None:
            logger.warning(
                f"Could not parse timestamp from filename: {path.name}. defaulting to Processing Time (NOW)."
            )

        # Setup temp paths
        start_time_epoch = time.time()
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
            # Use new Typed Config
            settings = config.birdnet

            # Sanitize location (None if disabled via -1 sentinel in default/env, but here validation ensures valid ranges or None)
            # Our Pydantic model allows None. If value is None, we pass None.
            # If value is -1 (from old default), we should treat as None?
            # Pydantic validator handles it? In `config.py` we allowed None.
            # Let's trust config.py logic.

            if bn_analyze:
                bn_analyze(
                    audio_input=str(temp_resampled),
                    min_conf=settings.min_conf,
                    lat=settings.lat,
                    lon=settings.lon,
                    week=settings.week,
                    overlap=settings.overlap,
                    sensitivity=settings.sensitivity,
                    threads=settings.threads,
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
                                scientific_name = row[2]

                                # Calculate Exact Timestamp
                                detection_timestamp = None
                                if file_start_time:
                                    # Timestamp = File Start + Detection Start Offset
                                    detection_timestamp = file_start_time + timedelta(
                                        seconds=start_t
                                    )

                                # Save Clip
                                clip_path = self._save_clip(
                                    temp_resampled, start_t, end_t, common_name
                                )

                                # Create Typed BirdDetection
                                detection = BirdDetection(
                                    filename=path.name,
                                    filepath=str(path),
                                    start_time=start_t,
                                    end_time=end_t,
                                    scientific_name=scientific_name,
                                    common_name=common_name,
                                    confidence=conf,
                                    lat=config.birdnet.lat,
                                    lon=config.birdnet.lon,
                                    clip_path=clip_path or None,  # Ensure None if empty string
                                    source_device=path.parent.name,  # Extract source from folder
                                    timestamp=detection_timestamp,
                                )

                                db.save_detection(detection)

                                # Check Watchlist & Alert
                                if db.is_watched(scientific_name):
                                    self._trigger_alert(detection)

                            except ValueError as e:
                                logger.warning(f"Skipping invalid row in {final_output_file}: {e}")
                            except Exception as e:
                                logger.error(f"Error processing detection: {e}")

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
            # Estimate audio duration
            try:
                info = sf.info(str(path))
                duration = info.duration
            except Exception:
                duration = 10.0  # Fallback

            processing_time = time.time() - start_time_epoch
            file_size = os.path.getsize(str(path))
            db.log_processed_file(path.name, duration, processing_time, file_size)
        except Exception as e:
            logger.error(f"Failed to log processing stats: {e}")

        # Cleanup
        try:
            if temp_resampled.exists():
                temp_resampled.unlink()
        except Exception:
            pass

    def _parse_timestamp_from_filename(
        self, filename: str, format_str: str = "%Y-%m-%d_%H-%M-%S"
    ) -> datetime | None:
        """
        Parses the timestamp from the filename.
        Expected format: YYYY-MM-DD_HH-MM-SS.flac or similar.
        """
        try:
            # Remove extension
            stem = Path(filename).stem
            # Attempt parse
            dt = datetime.strptime(stem, format_str)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            # Try to handle potential variations or fail gracefully
            return None

    def _save_clip(self, audio_path: Path, start_time: float, end_time: float, species: str) -> str:
        """Extracts and saves the audio clip for a detection.
        Returns the relative path to the clip or None if failed.
        """
        try:
            # Create clips directory if it doesn't exist
            # Note: CLIPS_DIR is guaranteed to be set by model_post_init
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

            # Return absolute path as string
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
        except Exception as e:
            logger.error(f"Resampling error: {e}")
            return False

    def _trigger_alert(self, detection: BirdDetection) -> None:
        """Creates a notification event in the shared queue."""
        try:
            # Redis Notification
            r = redis.Redis(host="silvasonic_redis", port=6379, db=0)

            # Use model_dump for clean dict, preserving aliases (lat/lon) and serializing datetimes
            data_dict = detection.model_dump(mode="json", by_alias=True)

            # Construct Alert Payload matching V2 spec
            # Title/Body for Apprise, plus raw data
            alert_payload = {
                "title": f"Bird Detected: {detection.common_name}",
                "body": f"Found {detection.common_name} ({detection.scientific_name}) with {detection.confidence:.2f} confidence.",
                "tag": "bird_detection",
                "timestamp": time.time(),
                "data": data_dict,
            }

            r.publish("alerts", json.dumps(alert_payload))

            logger.info(f"Triggered notification alert for {detection.common_name} via Redis")

        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
