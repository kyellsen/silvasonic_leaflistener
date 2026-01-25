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

# --- Logging ---
# --- Logging ---
# Ensure log directory exists (handled by volume, but safe to check)
os.makedirs("/var/log/silvasonic", exist_ok=True)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/silvasonic/recorder.log")
    ]
)
logger = logging.getLogger("recorder")

# --- Configuration ---
BASE_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", "/data/recording")

# --- Global State ---
running = True
STATUS_FILE = "/var/log/silvasonic/recorder_status.json"


def write_status(status: str, profile_name: str = "Unknown", 
                 device_desc: str = "Unknown", last_file: str = None):
    """Write current status to JSON file for dashboard."""
    try:
        data = {
            "timestamp": time.time(),
            "status": status,
            "profile": profile_name,
            "device": device_desc,
            "last_file": last_file,
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
        
        arecord_proc.stdout.close()
        
        ffmpeg_proc.wait()
        arecord_proc.wait()
        
        if ffmpeg_proc.returncode == 0:
            try:
                size_mb = os.path.getsize(filename) / 1024 / 1024
                logger.info(f"Saved: {os.path.basename(filename)} ({size_mb:.2f} MB)")
            except:
                logger.info(f"Saved: {os.path.basename(filename)}")
            return True
        else:
            stderr = ffmpeg_proc.stderr.read().decode()
            logger.error(f"FFmpeg error: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Recording error: {e}")
        return False


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
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory ready: {output_dir}")
    
    # Recording loop
    if profile.is_mock:
        logger.warning("🔧 MOCK MODE ENABLED - No real audio capture")
        write_status("Mocking", profile.name, "Virtual Mock Device")
        while running:
            filename = get_filename(output_dir, profile.recording.output_format)
            generate_mock_audio(
                filename,
                profile.recording.chunk_duration_seconds,
                profile.audio.sample_rate,
                profile.audio.channels
            )
            write_status("Mocking", profile.name, "Virtual Mock Device", os.path.basename(filename))
            time.sleep(1)
    else:
        if not device:
            logger.critical("No audio device found. Exiting.")
            write_status("Error: No Device", profile.name, "None")
            sys.exit(1)
        
        logger.info("🎙️ Recording started. Press Ctrl+C to stop.")
        write_status("Recording", profile.name, device.description)
        
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
                write_status("Recording", profile.name, device.description, os.path.basename(filename))
            elif running:
                logger.warning("Recording failed, retrying in 5s...")
                write_status("Retrying", profile.name, device.description)
                time.sleep(5)
    
    write_status("Stopped", profile.name, device.description if device else "Unknown")
    logger.info("👋 Shutdown complete.")


if __name__ == "__main__":
    main()
