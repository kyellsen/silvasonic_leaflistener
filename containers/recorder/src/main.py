"""The Ear - Audio Recorder for Silvasonic.

Records audio from USB microphones using a single continuous FFmpeg process.
Outputs:
1. FLAC files in 10s segments (User Critical Priority)
2. Raw PCM stream via UDP to Sound Analyser (Live Stream)
"""

import json
import logging
import logging.handlers
import os
import signal
import subprocess
import sys
import threading
import time
import typing
from dataclasses import asdict

import psutil

# --- Logging ---
logger = logging.getLogger("recorder")


def setup_logging() -> None:
    """Configure logging for the recorder service."""
    log_dir = "/var/log/silvasonic"
    # Allow override for tests if needed via env, or just try/except
    # But for now, just replicate existing logic shielded by function
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        pass  # Ignore if we can't create it (e.g. tests)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    log_file = os.path.join(log_dir, "recorder.log")
    try:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        handlers.append(file_handler)
    except Exception as e:
        logger.warning(f"Failed to setup file logging: {e}")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )


# --- Configuration ---
BASE_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", "/data/recording")
LIVE_STREAM_TARGET = os.getenv("LIVE_STREAM_TARGET", "silvasonic_livesound")
LIVE_STREAM_PORT = int(os.getenv("LIVE_STREAM_PORT", "1234"))

STATUS_DIR = "/mnt/data/services/silvasonic/status"


def ensure_status_dir() -> None:
    """Ensure the status directory exists."""
    try:
        os.makedirs(STATUS_DIR, exist_ok=True)
    except OSError:
        pass


# --- Global State ---
running = True
ffmpeg_process = None


def write_status(
    status: str, profile: typing.Any = None, device: typing.Any = None, last_file: str | None = None
) -> None:
    """Write current status to JSON file for dashboard.
    Uses 'recorder_{profile_slug}.json' or 'recorder.json' if no profile.
    """
    try:
        data = {
            "service": "recorder",
            "timestamp": time.time(),
            "status": status,
            "cpu_percent": psutil.cpu_percent(),
            "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
            "meta": {
                "profile": asdict(profile) if profile and hasattr(profile, "slug") else {},
                "device": asdict(device) if device and hasattr(device, "hw_address") else {},
                "mode": "Continuous + Live Stream",
            },
            "pid": os.getpid(),
        }

        # Determine filename
        rec_id = os.getenv("RECORDER_ID")
        if rec_id:
             filename = f"recorder_{rec_id}.json"
        else:
            slug = "default"
            if profile and hasattr(profile, "slug"):
                slug = profile.slug
            elif data["meta"].get("profile", {}).get("slug"):
                 slug = data["meta"]["profile"]["slug"]
            filename = f"recorder_{slug}.json"
            
        filepath = os.path.join(STATUS_DIR, filename)

        # Atomic write
        tmp_file = f"{filepath}.tmp"
        with open(tmp_file, "w") as f:
            json.dump(data, f)
        os.rename(tmp_file, filepath)
    except Exception as e:
        logger.error(f"Failed to write status: {e}")


def start_recording(
    profile: typing.Any, device: typing.Any, output_dir: str, strategy: typing.Any
) -> subprocess.Popen[bytes]:
    """Starts the continuous FFmpeg process."""
    global ffmpeg_process

    # Ensure output dir
    os.makedirs(output_dir, exist_ok=True)

    file_pattern = os.path.join(output_dir, "%Y-%m-%d_%H-%M-%S.flac")
    udp_url = f"udp://{LIVE_STREAM_TARGET}:{LIVE_STREAM_PORT}"

    # Get Input Args from Strategy
    input_args = strategy.get_ffmpeg_input_args()
    input_source = strategy.get_input_source()

    cmd = [
        "ffmpeg",
        # --- Input Strategy ---
        *input_args,
        "-i",
        input_source,
        # --- Output 1: Files (Segment Muxer) ---
        "-f",
        "segment",
        "-segment_time",
        str(profile.recording.chunk_duration_seconds),
        "-strftime",
        "1",
        "-c:a",
        "flac",
        "-compression_level",
        str(profile.recording.compression_level),
        file_pattern,
        # --- Output 2: Live Stream (UDP) ---
        "-f",
        "s16le",  # Raw PCM
        "-ac",
        "1",  # Force Mono for analysis simplicity
        "-ar",
        str(profile.audio.sample_rate),
        udp_url,
    ]

    logger.info(f"Starting Continuous Recording to {output_dir}")
    logger.info(f"Streaming to {udp_url}")
    logger.debug(f"CMD: {' '.join(cmd)}")

    # Needs stdin for FileMockStrategy
    ffmpeg_process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
    )

    # Start background tasks (e.g. file reading thread)
    strategy.start_background_tasks(ffmpeg_process)

    assert ffmpeg_process.stderr is not None
    return ffmpeg_process


def consume_stderr(proc: subprocess.Popen[bytes]) -> None:
    """Reads stderr in a separate thread to prevent buffer deadlock."""
    try:
        if proc.stderr is None:
            return
        for line in iter(proc.stderr.readline, b""):
            line_str = line.decode("utf-8", errors="replace").strip()
            if line_str:
                # Log everything for debugging
                logger.info(f"[FFmpeg] {line_str}")
    except Exception as e:
        logger.error(f"Log consumer error: {e}")
    finally:
        try:
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass


def main() -> None:
    """Start the Recorder service."""
    setup_logging()
    ensure_status_dir()
    global running, ffmpeg_process

    from .mic_profiles import create_strategy_for_profile, get_active_profile

    profile, device = get_active_profile()

    if not profile:
        logger.critical("No profile found.")
        sys.exit(1)

    # Create Strategy
    # Using type: ignore because mypy might not like dynamic imports inside function above, but here it's fine
    strategy = create_strategy_for_profile(profile, device)

    # Determine Output Directory
    # We prefer RECORDER_ID (e.g. "generic_usb_card1") to avoid collisions 
    # when multiple devices use the same profile.
    rec_id = os.getenv("RECORDER_ID")
    if rec_id:
        dir_name = rec_id
    else:
        dir_name = profile.slug
        
    output_dir = os.path.join(BASE_OUTPUT_DIR, dir_name)

    # Signal Handlers
    def stop(sig: int, frame: typing.Any) -> None:
        global running
        logger.info("Stopping...")
        running = False
        strategy.stop()  # Stop strategy threads
        if ffmpeg_process:
            ffmpeg_process.terminate()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    write_status("Starting", profile, device)

    while running:
        logger.info("Launching FFmpeg...")
        try:
            proc = start_recording(profile, device, output_dir, strategy)
            write_status("Recording", profile, device)
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            time.sleep(5)
            continue

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
