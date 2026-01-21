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
    import birdnet_analyzer.species as bn_species
except ImportError:
    bn_analyze = None
    bn_species = None

# DEBUG: Inspect bn_analyze at module load time
import inspect
if bn_analyze is not None:
    _bn_type = type(bn_analyze)
    _bn_is_module = inspect.ismodule(bn_analyze)
    _bn_has_analyze = hasattr(bn_analyze, 'analyze') if _bn_is_module else callable(bn_analyze)
    print(f"[DEBUG bn_analyze] Type: {_bn_type}, IsModule: {_bn_is_module}, HasAnalyze: {_bn_has_analyze}")
    if _bn_is_module and hasattr(bn_analyze, 'analyze'):
        print(f"[DEBUG bn_analyze.analyze] Signature: {inspect.signature(bn_analyze.analyze)}")
    elif callable(bn_analyze):
        print(f"[DEBUG bn_analyze (callable)] Signature: {inspect.signature(bn_analyze)}")

from src.config import config
from src.database import SessionLocal, Detection
from src.verify_audio import analyze_audio_quality

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

            # Load resampled file to check signal
            # Use the robust verifier
            quality_report = analyze_audio_quality(temp_resampled_path)
            
            logger.info(f"Signal Quality Check ({path.name} -> 48k):")
            logger.info(f"  RMS: {quality_report['rms']:.6f}")
            logger.info(f"  Max Amp: {quality_report['max_amp']:.6f}")
            if quality_report['warnings']:
                logger.warning(f"  WARNINGS: {'; '.join(quality_report['warnings'])}")
            
            if not quality_report['valid'] or quality_report['rms'] < 0.0001:
                 logger.warning(f"Audio appears invalid or dead silent. Skipping analysis to save resources.")
                 # We could return here, but maybe we let it run anyway just in case? 
                 # User said "birdnet py finds 0 segments", so let's run it BUT log heavily.
            else:
                 logger.info("  Signal looks valid for analysis.")

            # bn_analyze is the module, we need to call the analyze function inside it.
            # We use a very low min_conf here (0.01) to see EVERYTHING the model considers
            # Determine coordinates based on filter setting
            use_lat = config.LATITUDE if config.LOCATION_FILTER_ENABLED else None
            use_lon = config.LONGITUDE if config.LOCATION_FILTER_ENABLED else None
            
            # Generate Species List
            species_list = None
            if config.CUSTOM_SPECIES_LIST_PATH and Path(config.CUSTOM_SPECIES_LIST_PATH).exists():
                logger.info(f"Using custom species list from {config.CUSTOM_SPECIES_LIST_PATH}")
                # Assuming simple text file with one species per line or similar structure
                # For now, just logging it (implementation detail depends on format)
                # If it's a list argument for analyze(), passing the path might not work directly unless supported.
                # BirdNET-Analyzer 'analyze' usually takes a LIST of strings, not a path.
                try:
                    with open(config.CUSTOM_SPECIES_LIST_PATH, 'r') as f:
                        species_list = [line.strip() for line in f if line.strip()]
                except Exception as e:
                    logger.error(f"Failed to load custom species list: {e}")
                    
            elif config.LOCATION_FILTER_ENABLED and bn_species:
                try:
                    logger.info(f"Generating dynamic species list for Lat={use_lat}, Lon={use_lon}, Week={week}, Threshold={config.SPECIES_PRESENCE_THRESHOLD}")
                    species_list = bn_species.get_species_list(
                        lat=use_lat, 
                        lon=use_lon, 
                        week=week, 
                        threshold=config.SPECIES_PRESENCE_THRESHOLD
                    )
                    logger.info(f"Generated species list contains {len(species_list)} species.")
                except Exception as e:
                    logger.error(f"Failed to generate species list: {e}")
                    species_list = None 

            logger.info(f"Running BirdNET with Filter={config.LOCATION_FILTER_ENABLED}, Sensitivity={config.SENSITIVITY}, Lat={use_lat}, Lon={use_lon}, Week={week}")
            
            # bn_analyze is the MODULE birdnet_analyzer.analyze, not the function itself!
            # We must call bn_analyze.analyze() to invoke the actual analyze function.
            raw_detections = bn_analyze.analyze(
                audio_input=str(temp_resampled_path),
                min_conf=0.01,  # Use very low threshold to see all raw predictions
                lat=use_lat,
                lon=use_lon,
                week=week,
                overlap=config.SIG_OVERLAP,
                threads=config.THREADS,
                output=None
            )
            
            if raw_detections is None:
                raw_detections = {}

            # DEBUG: Deep inspection of raw_detections
            logger.info(f"[DEBUG] raw_detections type: {type(raw_detections)}")
            logger.info(f"[DEBUG] raw_detections repr (first 500 chars): {repr(raw_detections)[:500]}")
            if isinstance(raw_detections, dict) and raw_detections:
                first_key = next(iter(raw_detections))
                first_val = raw_detections[first_key]
                logger.info(f"[DEBUG] First key type: {type(first_key)}, value: {first_key}")
                logger.info(f"[DEBUG] First value type: {type(first_val)}, value: {repr(first_val)[:300]}")

            # Debug Logging: Show what we found
            logger.info(f"Raw analysis returned {len(raw_detections)} segments with > 0.01 confidence.")
            
            # Export raw results to CSV for inspection
            self._export_to_csv(raw_detections, path.name)

            for timestamp, preds in raw_detections.items():
                # entry is usually list of dicts or list of tuples
                # Log the top 3 predictions for this segment
                if preds:
                    # Sort by confidence just in case
                    sorted_preds = sorted(preds, key=lambda x: x.get('confidence', 0) if isinstance(x, dict) else x[1], reverse=True)
                    
                    top_n = sorted_preds[:5] # Log top 5
                    log_msg = f"Segment {timestamp}: Found {len(preds)} candidates. Top 5:"
                    for p in top_n:
                         if isinstance(p, dict):
                             log_msg += f"\n  - {p.get('common_name')} ({p.get('scientific_name')}): {p.get('confidence'):.4f}"
                         else:
                             log_msg += f"\n  - {p[0]}: {p[1]:.4f}"
                    logger.info(log_msg)

            # Filter for Database using the REAL config and SENSITIVITY
            # Effective Threshold = Base Config / Sensitivity
            # e.g. 0.7 / 1.0 = 0.7
            # e.g. 0.7 / 1.25 = 0.56 (More sensitive, allows lower confidence)
            effective_min_conf = max(0.01, config.MIN_CONFIDENCE / config.SENSITIVITY)
            effective_min_conf = min(0.99, effective_min_conf) # Clamp
            
            logger.info(f"Filtering with Effective Min Confidence={effective_min_conf:.4f} (Base={config.MIN_CONFIDENCE}, Sensitivity={config.SENSITIVITY})")

            final_detections = {}
            for timestamp, preds in raw_detections.items():
                valid_preds = []
                for p in preds:
                    conf = 0.0
                    if isinstance(p, dict):
                        conf = p.get('confidence', 0.0)
                    else:
                        conf = p[1] # Tuple (label, conf)
                    
                    if species_list and label not in species_list:
                         continue

                    if conf >= effective_min_conf:
                        valid_preds.append(p)
                
                if valid_preds:
                    final_detections[timestamp] = valid_preds

            self._save_detections(final_detections, path.name, recording_dt)
            logger.info(f"Analysis complete for {path.name}. Found {len(final_detections)} segments passing threshold {effective_min_conf:.4f}.")
            
        except Exception as e:
            logger.error(f"Error during analysis of {path.name}: {e}", exc_info=True)
        finally:
            # DEBUG: Keep resampled file for manual inspection
            logger.info(f"[DEBUG] Keeping temp file for inspection: {temp_resampled_path}")
            # Cleanup resampled file - DISABLED FOR DEBUG
            # if temp_resampled_path.exists():
            #     try:
            #         temp_resampled_path.unlink()
            #     except:
            #         pass
            # Cleanup param file if it exists in temp dir
            param_file = temp_dir / "BirdNET_analysis_params.csv"
            if param_file.exists():
                 try:
                    param_file.unlink()
                 except:
                    pass

    def _export_to_csv(self, detections, original_filename):
        """
        Manually export detections to a CSV file for easy inspection.
        """
        try:
            # Output directory mapped to host
            output_dir = Path("/data/db/results")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            csv_path = output_dir / f"{original_filename}.BirdNET.csv"
            
            with open(csv_path, 'w') as f:
                # Header
                f.write("Start (s),End (s),Label,Confidence,Common Name,Scientific Name\n")
                
                # Sort by time
                sorted_times = sorted(detections.keys())
                for timestamp in sorted_times:
                    start = timestamp[0]
                    end = timestamp[1]
                    preds = detections[timestamp]
                    
                    for p in preds:
                        if isinstance(p, dict):
                            label = p.get('label', '')
                            conf = p.get('confidence', 0)
                            com = p.get('common_name', '')
                            sci = p.get('scientific_name', '')
                        else:
                            # Tuple fallback
                            label = p[0]
                            conf = p[1]
                            com = label
                            sci = label
                            
                        f.write(f"{start},{end},\"{label}\",{conf:.4f},\"{com}\",\"{sci}\"\n")
            
            logger.info(f"Exported raw results to {csv_path}")
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")


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
