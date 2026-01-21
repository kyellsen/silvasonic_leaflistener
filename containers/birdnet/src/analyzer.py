import os
import datetime
from pathlib import Path
import soundfile as sf
import logging
import numpy as np

import subprocess

# BirdNET-Analyzer imports
try:
    import birdnet_analyzer.analyze as bn_analyze
except ImportError:
    bn_analyze = None

from src.config import config
from src.database import SessionLocal, Detection

logger = logging.getLogger("Analyzer")

class BirdNETAnalyzer:
    def __init__(self):
        logger.info("Initializing BirdNET Analyzer...")
        pass

    def process_file(self, file_path: str):
        """
        Analyze a single audio file and save detections to DB.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return

        try:
            info = sf.info(str(path))
            logger.info(f"Analyzing {path.name} | SR={info.samplerate}, Ch={info.channels}, Dur={info.duration:.2f}s, Format={info.format}")
        except Exception as e:
            logger.warning(f"Could not read audio info for {path.name}: {e}")
            # Continue anyway, let BirdNET try
            logger.info(f"Analyzing {path.name}...")
        
        # 1. Extract Timestamp
        recording_dt = self._parse_timestamp(path.name)
        if not recording_dt:
            logger.warning(f"Could not parse timestamp from {path.name}, using current time as fallback.")
            recording_dt = datetime.datetime.utcnow()
            
        # 2. Week of Year
        week = recording_dt.isocalendar()[1]
        
        # 3. Run Analysis
        # WORKAROUND: BirdNET tries to write 'BirdNET_analysis_params.csv' to the input dir.
        # Our input dir is Read-Only. We symlink the file to /tmp and analyze it there.
        temp_dir = Path("/tmp/birdnet_processing")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a resampled file for analysis
        temp_resampled_path = temp_dir / f"{path.stem}_48k.wav"
        
        try:
            # Explicitly resample to 48kHz using ffmpeg
            # This avoids issues where BirdNET/Librosa might choke on 384k files or create artifacts
            cmd = [
                "ffmpeg", "-y", 
                "-i", str(path.absolute()), 
                "-ar", "48000", 
                "-ac", "1", 
                str(temp_resampled_path)
            ]
            # Suppress ffmpeg output unless error
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"Resampled to 48kHz: {temp_resampled_path}")

            # bn_analyze is the function imported from birdnet_analyzer.analyze
            # We use a lower min_conf here to see what the model sees, then filter later
            logger.info(f"Running BirdNET with Lat={config.LATITUDE}, Lon={config.LONGITUDE}, Week={week}, Overlap={config.SIG_OVERLAP}, MinConf=0.1 (Debug Mode) on 48kHz input")
            
            raw_detections = bn_analyze(
                audio_input=str(temp_resampled_path), # Use RESAMPLED path
                min_conf=0.1, # LOW THRESHOLD FOR DEBUGGING
                lat=config.LATITUDE,
                lon=config.LONGITUDE,
                week=week,
                overlap=config.SIG_OVERLAP,
                threads=config.THREADS,
                output=None # Return results
            )
            
            if raw_detections is None:
                raw_detections = {}

            # Debug Logging: Show what we found
            logger.info(f"Raw analysis returned {len(raw_detections)} segments with > 0.1 confidence.")
            for timestamp, preds in raw_detections.items():
                # entry is usually list of dicts or list of tuples
                # Log the top prediction for this segment
                if preds:
                    top_pred = preds[0] # Assumes sorted or we just grab first
                    # Format for log
                    if isinstance(top_pred, dict):
                        lbl = f"{top_pred.get('common_name')} ({top_pred.get('confidence'):.2f})"
                    else:
                        lbl = str(top_pred)
                    logger.info(f"Segment {timestamp}: Top hit -> {lbl}")

            # Filter for Database using the REAL config
            final_detections = {}
            for timestamp, preds in raw_detections.items():
                valid_preds = []
                for p in preds:
                    conf = 0.0
                    if isinstance(p, dict):
                        conf = p.get('confidence', 0.0)
                    else:
                        conf = p[1] # Tuple (label, conf)
                    
                    if conf >= config.MIN_CONFIDENCE:
                        valid_preds.append(p)
                
                if valid_preds:
                    final_detections[timestamp] = valid_preds

            self._save_detections(final_detections, path.name, recording_dt)
            logger.info(f"Analysis complete for {path.name}. Found {len(final_detections)} segments passing threshold {config.MIN_CONFIDENCE}.")
            
        except Exception as e:
            logger.error(f"Error during analysis of {path.name}: {e}", exc_info=True)
        finally:
            # Cleanup resampled file
            if temp_resampled_path.exists():
                try:
                    temp_resampled_path.unlink()
                except:
                    pass
            # Cleanup param file if it exists in temp dir
            param_file = temp_dir / "BirdNET_analysis_params.csv"
            if param_file.exists():
                 try:
                    param_file.unlink()
                 except:
                    pass

    def _save_detections(self, detections, filename, recording_dt):
        """
        Save valid detections to SQLite.
        detections format expected: 
        { (start, end): [ {'common_name': '...', 'scientific_name': '...', 'confidence': 0.9}, ... ] }
        OR
        List of objects. We need to handle what `analyze_file` returns.
        
        Ref: BirdNET-Analyzer/birdnet_analyzer/analyze.py returns a dictionary:
        results[time_interval] = [(label, confidence), ...] usually.
        Wait, recent versions might have list of entries.
        
        Let's assume the dict format: {(start, end): [list of preds]}
        Where preds can be raw tuples or dicts.
        """
        session = SessionLocal()
        try:
            count = 0
            # Iterate over time segments
            for timestamp, preds in detections.items():
                start_time = timestamp[0]
                end_time = timestamp[1]
                
                # Preds is usually a list of predictions for that chunk.
                # Often we only care about the top one or ones above threshold (already filtered by analyze_file min_conf?)
                # analyze_file typically returns ALL > min_conf.
                
                for pred in preds:
                    # pred might be: {'common_name': 'X', 'scientific_name': 'Y', 'confidence': 0.8, 'label': 'X_Y'}
                    # or just a label string and confidence if raw.
                    # The library usually returns a list of dictionaries with full info if using the high level API.
                    
                    # Defensively handle data structure
                    if isinstance(pred, dict):
                        sci = pred.get('scientific_name', '')
                        com = pred.get('common_name', '')
                        conf = pred.get('confidence', 0.0)
                        label = pred.get('label', f"{com} ({sci})")
                    else:
                        # Fallback if it's a simple tuple (Label, Conf)
                        # Label often "Common_Scientific"
                        label_raw = pred[0]
                        conf = pred[1]
                        parts = label_raw.split('_')
                        if len(parts) >= 2:
                            sci = parts[-1] 
                            com = "_".join(parts[:-1])
                        else:
                            sci = label_raw
                            com = label_raw
                        label = label_raw

                    if conf >= config.MIN_CONFIDENCE:
                        det = Detection(
                            recording_timestamp=recording_dt,
                            filename=filename,
                            start_time=start_time,
                            end_time=end_time,
                            scientific_name=sci,
                            common_name=com,
                            label=label,
                            confidence=float(conf)
                        )
                        session.add(det)
                        count += 1
            
            session.commit()
            if count > 0:
                logger.info(f"Saved {count} detections to DB.")
                
        except Exception as e:
            logger.error(f"Database error: {e}")
            session.rollback()
        finally:
            session.close()

    def _parse_timestamp(self, filename: str):
        """
        Try to parse timestamp from filenames like:
        - silvasonic_2024-01-21_12-00-00.flac
        - 20240121_120000.wav
        """
        # Clean extension
        name = Path(filename).stem
        
        # Pattern 1: YYYY-MM-DD_HH-MM-SS (Silvasonic standard)
        # We search for the pattern using regex or split
        # "silvasonic_2024-01-21_12-00-00" -> split by '_'
        parts = name.split('_')
        # Look for parts that look like dates
        for i in range(len(parts)-1):
            d_part = parts[i]
            t_part = parts[i+1]
            try:
                # Try 2024-01-21 12-00-00
                dt_str = f"{d_part} {t_part}"
                return datetime.datetime.strptime(dt_str, "%Y-%m-%d %H-%M-%S")
            except ValueError:
                pass
                
        # Pattern 2: YYYYMMDD_HHMMSS
        # Try to find a continuous digit string
        import re
        match = re.search(r"(\d{8})_(\d{6})", name)
        if match:
            try:
                return datetime.datetime.strptime(f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M%S")
            except ValueError:
                pass
                
        return None
