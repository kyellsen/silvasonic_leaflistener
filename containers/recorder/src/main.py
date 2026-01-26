"""
The Ear - Audio Recorder for Silvasonic

Records audio from USB microphones using a single continuous FFmpeg process.
Outputs:
1. FLAC files in 30s segments (User Critical Priority)
2. Raw PCM stream via UDP to Sound Analyser (Live Stream)
"""

import os
import sys
import subprocess
import time
import datetime
import signal
import logging
import psutil
import json
import socket
import threading
from dataclasses import asdict

# --- Logging ---
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
LIVE_STREAM_TARGET = os.getenv("LIVE_STREAM_TARGET", "silvasonic_sound_analyser")
LIVE_STREAM_PORT = int(os.getenv("LIVE_STREAM_PORT", "1234"))

STATUS_FILE = "/mnt/data/services/silvasonic/status/recorder.json"
os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)

# --- Global State ---
running = True
ffmpeg_process = None

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
                "profile": asdict(profile) if profile and hasattr(profile, 'slug') else {},
                "device": asdict(device) if device and hasattr(device, 'hw_address') else {},
                "mode": "Continuous + Live Stream"
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



def start_recording(profile, device, output_dir):
    """
    Starts the continuous FFmpeg process.
    """
    global ffmpeg_process
    
    # Ensure output dir
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Input: ALSA Device
    # 2. Output 1: Segment Muxer (FLAC files)
    # 3. Output 2: UDP Stream (Raw PCM)
    
    # Filename Pattern for strftime
    # We use %Y-%m-%d_%H-%M-%S.flac
    # Note: We must escape % for python string formatting if needed, but here it's fine.
    
    file_pattern = os.path.join(output_dir, "%Y-%m-%d_%H-%M-%S.flac")
    
    # Use hostname directly, let FFmpeg resolve it
    udp_url = f"udp://{LIVE_STREAM_TARGET}:{LIVE_STREAM_PORT}"
    
    cmd = [
        "ffmpeg",
        "-f", "alsa",
        "-ac", str(profile.audio.channels),
        "-ar", str(profile.audio.sample_rate),
        "-i", device.hw_address,
        
        # Audio Filtering (Optional: Highpass/Denoise? No, keep it raw for analysis)
        
        # --- Output 1: Files (Segment Muxer) ---
        "-f", "segment",
        "-segment_time", str(profile.recording.chunk_duration_seconds), # Should be 30
        "-strftime", "1",
        "-c:a", "flac",
        "-compression_level", str(profile.recording.compression_level),
        file_pattern,
        
        # --- Output 2: Live Stream (UDP) ---
        "-f", "s16le",       # Raw PCM
        "-ac", "1",          # Force Mono for analysis simplicity
        "-ar", str(profile.audio.sample_rate),
        udp_url
    ]
    
    if profile.is_mock:
         # Replace input with lavfi noise
         cmd[1] = "lavfi"
         cmd[2] = f"anoisesrc=c=pink:r={profile.audio.sample_rate}:a=0.1"
         logger.warning("🔧 MOCK Source Enabled")

    logger.info(f"Starting Continuous Recording to {output_dir}")
    logger.info(f"Streaming to {udp_url}")
    logger.debug(f"CMD: {' '.join(cmd)}")
    logger.info(f"CMD_DEBUG: {' '.join(cmd)}") # Temporary Debug
    logger.info(f"PROFILE_DEBUG: Channels={profile.audio.channels} Rate={profile.audio.sample_rate}")
    
    # Use Popen
    ffmpeg_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    return ffmpeg_process

def consume_stderr(proc):
    """
    Reads stderr in a separate thread to prevent buffer deadlock.
    """
    try:
        for line in iter(proc.stderr.readline, b''):
            line_str = line.decode('utf-8', errors='replace').strip()
            if line_str:
                # Log everything for debugging
                logger.info(f"[FFmpeg] {line_str}")
    except Exception as e:
        logger.error(f"Log consumer error: {e}")
    finally:
        try:
            proc.stderr.close()
        except:
            pass

def main():
    global running, ffmpeg_process
    
    from mic_profiles import get_active_profile
    profile, device = get_active_profile()
    
    if not profile:
        logger.critical("No profile found.")
        sys.exit(1)
        
    output_dir = os.path.join(BASE_OUTPUT_DIR, profile.slug)
    
    # Signal Handlers
    def stop(sig, frame):
        global running
        logger.info("Stopping...")
        running = False
        if ffmpeg_process:
            ffmpeg_process.terminate()
            
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    write_status("Starting", profile, device)
    
    while running:
        logger.info("Launching FFmpeg...")
        proc = start_recording(profile, device, output_dir)
        write_status("Recording", profile, device)
        
        # Monitor Loop
        # Start log consumer thread
        log_thread = threading.Thread(target=consume_stderr, args=(proc,), daemon=True)
        log_thread.start()

        try:
             # Loop while process is running
             while running and proc.poll() is None:
                 write_status("Recording", profile, device)
                 time.sleep(5)

        except Exception as e:
            logger.error(f"Monitor Loop Error: {e}")
            
        if not running:
            break
            
        if not running:
            break
            
        # Cleanup
        if running: 
            logger.warning(f"FFmpeg exited with code {proc.returncode}. Restarting in 5s...")
        
        # Determine if we should print stderr manually (only if thread missed it/implementation changed)
        # But our thread covers it.


        write_status("Error: Restarting", profile, device)
        time.sleep(5)

    write_status("Stopped", profile, device)

if __name__ == "__main__":
    main()
