
import os
import sys
import subprocess
import time
import datetime
import signal
import logging
import re

# --- Configuration ---
RAW_DIR = "/data/recording"
SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLERATE", "384000"))
CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
BIT_DEPTH = int(os.getenv("AUDIO_BIT_DEPTH", "16"))
DEVICE_PATTERNS = os.getenv("AUDIO_DEVICE_PATTERNS", "UltraMic,Dodotronic,384K").split(",")
CHUNK_DURATION = int(os.getenv("AUDIO_CHUNK_SECONDS", "60"))
MOCK_HARDWARE = os.getenv("MOCK_HARDWARE", "false").lower() == "true"

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("recorder")

# --- Global State ---
running = True

def get_filename():
    """Generates a timestamped filename."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(RAW_DIR, f"{timestamp}.flac")

def find_audio_device():
    """Find audio device using arecord -l, matching against patterns."""
    try:
        result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
        lines = result.stdout + result.stderr
        
        logger.info("Scanning for audio devices...")
        logger.debug(f"arecord -l output:\n{lines}")
        
        for line in lines.split('\n'):
            for pattern in DEVICE_PATTERNS:
                if pattern.lower() in line.lower():
                    # Extract card number
                    match = re.search(r'card (\d+)', line)
                    if match:
                        card_id = match.group(1)
                        logger.info(f"Found device matching '{pattern}': {line.strip()}")
                        logger.info(f"Using hw:{card_id},0")
                        return f"hw:{card_id},0"
        
        logger.error("No matching audio device found!")
        logger.info("Available devices:")
        logger.info(lines)
        return None
        
    except Exception as e:
        logger.error(f"Error scanning devices: {e}")
        return None

def record_chunk(device, filename, duration):
    """Record a chunk using arecord piped to ffmpeg for FLAC encoding."""
    
    # arecord -> raw PCM, pipe to ffmpeg for FLAC
    arecord_cmd = [
        "arecord",
        "-D", device,
        "-f", f"S{BIT_DEPTH}_LE",  # Signed, Little Endian
        "-r", str(SAMPLE_RATE),
        "-c", str(CHANNELS),
        "-d", str(duration),
        "-t", "raw",  # Output raw PCM
        "-q",  # Quiet
        "-"  # Output to stdout
    ]
    
    ffmpeg_cmd = [
        "ffmpeg",
        "-f", f"s{BIT_DEPTH}le",  # Input format
        "-ar", str(SAMPLE_RATE),
        "-ac", str(CHANNELS),
        "-i", "pipe:0",  # Read from stdin
        "-y",  # Overwrite
        "-c:a", "flac",
        "-compression_level", "5",
        filename
    ]
    
    logger.info(f"Recording {duration}s to {filename}")
    
    try:
        # Pipe arecord output to ffmpeg
        arecord_proc = subprocess.Popen(arecord_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=arecord_proc.stdout, 
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Allow arecord to receive SIGPIPE if ffmpeg exits
        arecord_proc.stdout.close()
        
        # Wait for completion
        ffmpeg_proc.wait()
        arecord_proc.wait()
        
        if ffmpeg_proc.returncode == 0:
            # Get file size
            try:
                size = os.path.getsize(filename)
                logger.info(f"Saved: {filename} ({size / 1024 / 1024:.2f} MB)")
            except:
                logger.info(f"Saved: {filename}")
            return True
        else:
            stderr = ffmpeg_proc.stderr.read().decode()
            logger.error(f"FFmpeg error: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Recording error: {e}")
        return False

def generate_mock_audio(filename, duration):
    """Generate white noise for testing without hardware."""
    import numpy as np
    import soundfile as sf
    
    logger.info(f"[MOCK] Generating {duration}s noise to {filename}")
    
    samples = int(SAMPLE_RATE * duration)
    noise = np.random.uniform(-0.5, 0.5, (samples, CHANNELS)).astype('float32')
    
    sf.write(filename, noise, SAMPLE_RATE, subtype='PCM_16')
    logger.info(f"[MOCK] Saved: {filename}")

def main():
    global running
    
    logger.info("=" * 50)
    logger.info("Starting 'The Ear' (ALSA Backend)")
    logger.info("=" * 50)
    logger.info(f"Config: Rate={SAMPLE_RATE}, Ch={CHANNELS}, Bit={BIT_DEPTH}")
    logger.info(f"Device patterns: {DEVICE_PATTERNS}")
    logger.info(f"Chunk duration: {CHUNK_DURATION}s")
    logger.info(f"Storage: {RAW_DIR}")
    logger.info(f"Mock mode: {MOCK_HARDWARE}")
    
    # Handle Signals
    def signal_handler(sig, frame):
        global running
        logger.info("Signal received, stopping after current chunk...")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure output directory exists
    os.makedirs(RAW_DIR, exist_ok=True)
    
    if MOCK_HARDWARE:
        logger.warning("!!! MOCK MODE ENABLED !!!")
        while running:
            filename = get_filename()
            generate_mock_audio(filename, CHUNK_DURATION)
            time.sleep(1)  # Small pause between chunks
    else:
        # Find device
        device = find_audio_device()
        if not device:
            logger.critical("Cannot continue without audio device. Exiting.")
            sys.exit(1)
        
        logger.info("Recording started. Press Ctrl+C to stop.")
        
        while running:
            filename = get_filename()
            success = record_chunk(device, filename, CHUNK_DURATION)
            
            if not success and running:
                logger.warning("Recording failed, retrying in 5s...")
                time.sleep(5)
    
    logger.info("Shutdown complete.")

if __name__ == "__main__":
    main()
