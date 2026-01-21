import os
import datetime
from pathlib import Path
import logging
import numpy as np

# BirdNET-Analyzer imports
try:
    import birdnet_analyzer.analyze as bn_analyze
except ImportError:
    pass

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

        logger.info(f"Analyzing {path.name}...")
        
        # 1. Extract Timestamp
        recording_dt = self._parse_timestamp(path.name)
        if not recording_dt:
            logger.warning(f"Could not parse timestamp from {path.name}, using current time as fallback.")
            recording_dt = datetime.datetime.utcnow()
            
        # 2. Week of Year
        week = recording_dt.isocalendar()[1]
        
        # 3. Run Analysis
        try:
            # bn_analyze is the function imported from birdnet_analyzer.analyze
            detections = bn_analyze(
                audio_input=str(path),
                min_conf=config.MIN_CONFIDENCE,
                lat=config.LATITUDE,
                lon=config.LONGITUDE,
                week=week,
                overlap=config.SIG_OVERLAP,
                threads=config.THREADS,
                output=None
            )
            
            self._save_detections(detections, path.name, recording_dt)
            logger.info(f"Analysis complete for {path.name}. Found {len(detections)} potential segments.")
            
        except Exception as e:
            logger.error(f"Error during analysis of {path.name}: {e}", exc_info=True)

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
