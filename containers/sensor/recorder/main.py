
import os
import sys
import queue
import time
import threading
import datetime
import signal
import logging
import numpy as np
import sounddevice as sd
import soundfile as sf

# --- Configuration ---
RAW_DIR = "/data/recording"
SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLERATE", "384000"))
CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
DEVICE_NAME = os.getenv("AUDIO_DEVICE_NAME", "Ultramic") # Substring match
SUBTYPE = os.getenv("AUDIO_SUBTYPE", "PCM_16") 
MOCK_HARDWARE = os.getenv("MOCK_HARDWARE", "false").lower() == "true"
BUFFER_SIZE_SECONDS = 5 # How much audio to buffer in RAM before potential dropouts
BLOCK_DURATION_MS = 100 # Approx duration of each callback block

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("recorder")

# --- Global State ---
audio_queue = queue.Queue(maxsize=int(SAMPLE_RATE * BUFFER_SIZE_SECONDS / (SAMPLE_RATE * BLOCK_DURATION_MS / 1000))) 
running = True
current_filename = None

def get_filename():
    """Generates a timestamped filename."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(RAW_DIR, f"{timestamp}.flac")

def audio_callback(indata, frames, time_info, status):
    """Callback function for sounddevice. Runs in a separate thread."""
    if status:
        logger.warning(f"Audio Callback Status: {status}")
    
    # Place a copy of the data in the queue
    try:
        audio_queue.put_nowait(indata.copy())
    except queue.Full:
        logger.error("BUFFER OVERFLOW: Audio queue is full! Dropping frames.")

def file_writer():
    """Consumer thread that writes audio data to disk."""
    global current_filename
    
    # Ensure output directory exists
    os.makedirs(RAW_DIR, exist_ok=True)
    
    logger.info("Writer thread started.")
    
    while running or not audio_queue.empty():
        try:
            # Generate new file if needed (e.g., could implement file rotation here, 
            # currently we just start one file and write 'forever' until restart/signal, 
            # OR we can make a new file every X minutes. 
            # For simplicity MVP, we'll stream to one file per session, 
            # but usually for bioacoustics we want chunked files (e.g. 1 min or 5 min).
            # Let's Implement basic chunking logic: New file every 1 minute for safety?
            # User rq didn't specify, but "record logic" usually implies manageable files.
            # Let's stick to one file per run for MVP as per plan, or maybe rotational?
            # Re-reading: "Write FLAC files". Plural. Let's do a simple rotation every minute to be safe?
            # Actually, continuous stream to one file is risky if crash. 
            # Let's do 60s chunks.
            
            chunk_start_time = time.time()
            filename = get_filename()
            logger.info(f"Starting new recording: {filename}")
            
            with sf.SoundFile(filename, mode='w', samplerate=SAMPLE_RATE, channels=CHANNELS, subtype=SUBTYPE) as file:
                while time.time() - chunk_start_time < 60 and running:
                    try:
                        data = audio_queue.get(timeout=1)
                        file.write(data)
                    except queue.Empty:
                        continue
            
            logger.info(f"Finished writing: {filename}")
            
        except Exception as e:
            logger.error(f"Writer Error: {e}")
            time.sleep(1)

def main():
    global running
    
    logger.info("Starting 'The Ear'...")
    logger.info(f"Config: Rate={SAMPLE_RATE}, Ch={CHANNELS}, Device='{DEVICE_NAME}'")
    logger.info(f"Storage: {RAW_DIR}")
    
    # Handle Signals
    def signal_handler(sig, frame):
        global running
        logger.info("Signal received, stopping...")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    writer_thread = threading.Thread(target=file_writer)
    writer_thread.start()

    try:
        if MOCK_HARDWARE:
            logger.warning("!!! MOCK MODE ENABLED !!! Generating white noise.")
            # Simulate streaming audio
            while running:
                # Generate random noise block
                block_size = int(SAMPLE_RATE * BLOCK_DURATION_MS / 1000)
                noise = np.random.uniform(-0.1, 0.1, (block_size, CHANNELS)).astype('float32')
                
                # Direct put to queue
                try:
                    audio_queue.put(noise, timeout=1)
                except queue.Full:
                     logger.error("BUFFER OVERFLOW (MOCK): Queue full")
                
                # Sleep to simulate real-time
                time.sleep(BLOCK_DURATION_MS / 1000)
                
        else:
            # Find Device
            devices = sd.query_devices()
            target_device_idx = None
            for idx, dev in enumerate(devices):
                if DEVICE_NAME.lower() in dev['name'].lower() and dev['max_input_channels'] >= CHANNELS:
                    target_device_idx = idx
                    logger.info(f"Found target device: {dev['name']} (Index {idx})")
                    break
            
            if target_device_idx is None:
                logger.error(f"Device containing '{DEVICE_NAME}' not found!")
                logger.info("Available devices:")
                logger.info(devices)
                # Fallback? No, this is critical.
                # But for dev purposes, if not found, we might want to crash loop.
                # However, if user said "other devices", maybe default to default input?
                # Let's stick to fail-fast if specific device required, or use default if DEVICE_NAME is empty.
                if not DEVICE_NAME:
                     target_device_idx = None # Use default
                     logger.info("Using System Default Input Device")
                else: 
                     sys.exit(1)

            with sd.InputStream(device=target_device_idx,
                                channels=CHANNELS,
                                samplerate=SAMPLE_RATE,
                                callback=audio_callback,
                                blocksize=int(SAMPLE_RATE * BLOCK_DURATION_MS / 1000)):
                logger.info("Recording started. Press Ctrl+C to stop.")
                while running:
                    sd.sleep(1000)
                    
    except Exception as e:
        logger.critical(f"Fatal Recorder Error: {e}")
        running = False
    
    finally:
        logger.info("Waiting for writer to finish...")
        writer_thread.join()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    main()
