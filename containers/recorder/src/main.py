"""
The Ear - Audio Recorder for Silvasonic

Records audio from USB microphones, auto-detecting device configuration
from microphone profiles. Outputs FLAC files in configurable chunks.

Each microphone records to its own subfolder based on the profile slug.
"""

import os
import sys
import subprocess
import time
import datetime
import signal
import logging
import numpy as np
import json
from dataclasses import asdict

# --- Logging ---
# Ensure log directory exists (handled by volume, but safe to check)
os.makedirs("/var/log/silvasonic", exist_ok=True)

import logging.handlers

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.TimedRotatingFileHandler(
            "/var/log/silvasonic/recorder.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger("recorder")

# --- Configuration ---
BASE_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", "/data/recording")

# --- Global State ---
running = True
import psutil

STATUS_FILE = "/mnt/data/services/silvasonic/status/recorder.json"

# Ensure dir exists (it should via volume, but good practice)
os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)

def write_status(status: str, profile=None, device=None, last_file: str = None):
    """Write current status to JSON file for dashboard."""
    try:
        data = {
            "service": "recorder",
            "timestamp": time.time(),
            "status": status,
            "cpu_percent": psutil.cpu_percent(),
            "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
            "meta": {
                "profile": asdict(profile) if profile and hasattr(profile, 'slug') else {"name": profile_name} if profile_name != "Unknown" else {},
                "device": asdict(device) if device and hasattr(device, 'hw_address') else {"description": device_desc} if device_desc != "Unknown" else {},
                "last_file": last_file
            },
            "pid": os.getpid()
        }
        # Atomic write
        tmp_file = f"{STATUS_FILE}.tmp"
        with open(tmp_file, 'w') as f:
            json.dump(data, f)
        os.rename(tmp_file, STATUS_FILE)
    except Exception as e:
        logger.error(f"Failed to write status: {e}")


def get_output_dir(profile_slug: str) -> str:
    """Get output directory for a specific microphone profile."""
    return os.path.join(BASE_OUTPUT_DIR, profile_slug)


def get_filename(output_dir: str, output_format: str = "flac") -> str:
    """Generates a timestamped filename."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(output_dir, f"{timestamp}.{output_format}")


def record_chunk(device_hw: str, filename: str, duration: int,
                 sample_rate: int, channels: int, bit_depth: int,
                 compression_level: int = 5) -> bool:
    """
    Record a chunk using arecord piped to ffmpeg for FLAC encoding.
    """
    arecord_cmd = [
        "arecord",
        "-D", device_hw,
        "-f", f"S{bit_depth}_LE",
        "-r", str(sample_rate),
        "-c", str(channels),
        "-d", str(duration),
        "-t", "raw",
        "-q",
        "-"
    ]
    
    ffmpeg_cmd = [
        "ffmpeg",
        "-f", f"s{bit_depth}le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-i", "pipe:0",
        "-y",
        "-c:a", "flac",
        "-compression_level", str(compression_level),
        "-loglevel", "warning",
        filename
    ]
    
    logger.info(f"Recording {duration}s -> {os.path.basename(filename)}")
    
    arecord_proc = None
    ffmpeg_proc = None

    try:
        arecord_proc = subprocess.Popen(
            arecord_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd, 
            stdin=arecord_proc.stdout,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        # Allow arecord to receive SIGPIPE if ffmpeg dies
        if arecord_proc.stdout:
            arecord_proc.stdout.close()
        
        # Wait for processes with timeout (duration + 5s buffer)
        try:
            _, stderr = ffmpeg_proc.communicate(timeout=duration + 5)
            
            # Wait for arecord to finish (should be done if ffmpeg is done reading)
            arecord_proc.wait(timeout=2)
            
        except subprocess.TimeoutExpired:
            logger.error("Recording process timed out - killing...")
            return False

        if arecord_proc.returncode != 0:
            arecord_err = arecord_proc.stderr.read().decode() if arecord_proc.stderr else "Unknown"
            logger.error(f"Arecord error (code {arecord_proc.returncode}): {arecord_err}")
            return False

        if ffmpeg_proc.returncode == 0:
            try:
                if os.path.exists(filename):
                    size_mb = os.path.getsize(filename) / 1024 / 1024
                    logger.info(f"Saved: {os.path.basename(filename)} ({size_mb:.2f} MB)")
                else:
                     logger.error("FFmpeg exited 0 but file not found!")
                     return False
            except Exception as e:
                logger.warning(f"Error checking file size: {e}")
            return True
        else:
            err_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"FFmpeg error (code {ffmpeg_proc.returncode}): {err_msg}")
            return False
            
    except Exception as e:
        logger.error(f"Recording error: {e}")
        return False
    finally:
        # cleanup processes if still running
        for p in [arecord_proc, ffmpeg_proc]:
            if p is not None and p.poll() is None:
                try:
                    p.terminate()
                    p.wait(timeout=1)
                except:
                    try:
                        p.kill()
                    except:
                        pass


def generate_mock_audio(filename: str, duration: int, 
                        sample_rate: int, channels: int) -> bool:
    """Generate synthetic audio for testing."""
    try:
        import soundfile as sf
        
        logger.info(f"[MOCK] Generating {duration}s -> {os.path.basename(filename)}")
        
        samples = int(sample_rate * duration)
        noise = np.random.uniform(-0.3, 0.3, (samples, channels)).astype('float32')
        
        # Add a faint test tone
        t = np.linspace(0, duration, samples)
        tone = 0.05 * np.sin(2 * np.pi * 440 * t)
        noise[:, 0] += tone.astype('float32')
        
        sf.write(filename, noise, sample_rate, subtype='PCM_16')
        
        size_mb = os.path.getsize(filename) / 1024 / 1024
        logger.info(f"[MOCK] Saved: {os.path.basename(filename)} ({size_mb:.2f} MB)")
        return True
        
    except Exception as e:
        logger.error(f"Mock generation error: {e}")
        return False


def main():
    global running
    
    # Import profile loader
    from mic_profiles import get_active_profile
    
    profile, device = get_active_profile()
    
    if profile is None:
        logger.critical("No microphone profile available. Exiting.")
        sys.exit(1)
    
    # Determine output directory based on profile
    output_dir = get_output_dir(profile.slug)
    
    # Print configuration
    logger.info("=" * 60)
    logger.info("🎤 THE EAR - Silvasonic Audio Recorder")
    logger.info("=" * 60)
    logger.info(f"Profile: {profile.name}")
    logger.info(f"  Slug: {profile.slug}")
    logger.info(f"  Manufacturer: {profile.manufacturer}")
    logger.info(f"  Sample Rate: {profile.audio.sample_rate} Hz")
    logger.info(f"  Channels: {profile.audio.channels}")
    logger.info(f"  Bit Depth: {profile.audio.bit_depth}")
    logger.info(f"  Chunk Duration: {profile.recording.chunk_duration_seconds}s")
    logger.info(f"  Output Format: {profile.recording.output_format}")
    logger.info(f"  Output Directory: {output_dir}")
    
    if device:
        logger.info(f"  Device: {device.hw_address}")
        logger.info(f"  Description: {device.description}")
    
    logger.info(f"  Mock Mode: {profile.is_mock}")
    logger.info("=" * 60)
    
    # Signal handlers
    def signal_handler(sig, frame):
        global running
        logger.info("Signal received, stopping after current chunk...")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure output directory exists
    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory ready: {output_dir}")
    except OSError as e:
        logger.critical(f"Could not create output directory {output_dir}: {e}")
        sys.exit(1)
    
    # Recording loop
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 10
    
    if profile.is_mock:
        logger.warning("🔧 MOCK MODE ENABLED - No real audio capture")
        write_status("Mocking", profile, device)
        while running:

            filename = get_filename(output_dir, profile.recording.output_format)
            if generate_mock_audio(
                filename,
                profile.recording.chunk_duration_seconds,
                profile.audio.sample_rate,
                profile.audio.channels
            ):
                write_status("Mocking", profile, device, os.path.basename(filename))
                consecutive_errors = 0
            else:
                 consecutive_errors += 1
            
            time.sleep(1)
    else:
        if not device:
            logger.critical("No audio device found. Exiting.")
            write_status("Error: No Device", profile, None)
            sys.exit(1)
        
        logger.info("🎙️ Recording started. Press Ctrl+C to stop.")
        write_status("Recording", profile, device)
        
        while running:

            filename = get_filename(output_dir, profile.recording.output_format)
            success = record_chunk(
                device_hw=device.hw_address,
                filename=filename,
                duration=profile.recording.chunk_duration_seconds,
                sample_rate=profile.audio.sample_rate,
                channels=profile.audio.channels,
                bit_depth=profile.audio.bit_depth,
                compression_level=profile.recording.compression_level,
            )
            
            if success:
                write_status("Recording", profile, device, os.path.basename(filename))
                consecutive_errors = 0
            else:
                consecutive_errors += 1
                logger.warning(f"Recording failed ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS})")
                
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.critical("Too many consecutive errors. Exiting to trigger restart.")
                    write_status("Fatal Error", profile, device)
                    sys.exit(1)
                    
                if running:
                    write_status("Retrying", profile, device)
                    time.sleep(5)
    
    write_status("Stopped", profile, device)
    logger.info("👋 Shutdown complete.")


if __name__ == "__main__":
    main()
