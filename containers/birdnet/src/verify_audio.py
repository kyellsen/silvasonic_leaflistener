
import os
import sys
import numpy as np
import soundfile as sf
from pathlib import Path
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AudioCheck")

def analyze_audio_quality(file_path):
    """
    Load an audio file and check for common issues.
    Returns a dictionary with stats and warnings.
    """
    path = Path(file_path)
    results = {
        "rms": 0.0,
        "max_amp": 0.0,
        "dc_offset": 0.0,
        "samplerate": 0,
        "duration": 0.0,
        "channels": 0,
        "warnings": [],
        "valid": False
    }

    if not path.exists():
        results["warnings"].append(f"File not found: {path}")
        return results

    try:
        # Load header info
        info = sf.info(str(path))
        results["samplerate"] = info.samplerate
        results["channels"] = info.channels
        results["duration"] = info.duration
        
        # Read data
        data, rate = sf.read(str(path))
        
        # 1. Check for valid data
        if len(data) == 0:
            results["warnings"].append("File is empty (0 samples).")
            return results
        
        results["valid"] = True

        # 2. Check for Silence (RMS)
        rms = np.sqrt(np.mean(data**2))
        results["rms"] = float(rms)
        if rms < 0.001:
            results["warnings"].append("Silence detected (RMS < 0.001)")

        # 3. Check for Clipping
        max_amp = np.max(np.abs(data))
        results["max_amp"] = float(max_amp)
        if max_amp >= 1.0:
            results["warnings"].append("Clipping detected (Max Amp >= 1.0)")
        elif max_amp < 0.05:
            results["warnings"].append("Low signal level (Max Amp < 0.05)")

        # 4. Check for DC Offset
        mean_amp = np.mean(data)
        results["dc_offset"] = float(mean_amp)
        if abs(mean_amp) > 0.1:
            results["warnings"].append(f"Significant DC Offset ({mean_amp:.4f})")

        return results

    except Exception as e:
        results["warnings"].append(f"Error reading file: {e}")
        return results

def check_structure(file_path):
    """Legacy wrapper for CLI usage"""
    res = analyze_audio_quality(file_path)
    logger.info(f"Analysis for {file_path}:")
    logger.info(f"  - Valid: {res['valid']}")
    logger.info(f"  - RMS: {res['rms']:.6f}")
    logger.info(f"  - Max Amp: {res['max_amp']:.6f}")
    for w in res['warnings']:
        logger.warning(f"  [WARN] {w}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python verify_audio.py <file_or_directory>")
        sys.exit(1)
    
    target = Path(sys.argv[1])
    
    if target.is_dir():
        files = list(target.glob("*.wav")) + list(target.glob("*.flac"))
        if not files:
             logger.warning("No .wav or .flac files found in directory.")
        for f in files:
            check_structure(f)
            print("-" * 40)
    else:
        check_structure(target)
