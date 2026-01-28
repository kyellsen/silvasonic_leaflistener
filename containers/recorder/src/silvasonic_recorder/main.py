"""The Recorder - Audio Recorder for Silvasonic.

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

import psutil
import structlog

from silvasonic_recorder.mic_profiles import (
    DetectedDevice,
    MicrophoneProfile,
    create_strategy_for_profile,
    get_active_profile,
)

# --- Configuration ---
BASE_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", "/data/recording")
LIVE_STREAM_TARGET = os.getenv("LIVE_STREAM_TARGET", "silvasonic_livesound")
LIVE_STREAM_PORT = int(os.getenv("LIVE_STREAM_PORT", "1234"))
STATUS_DIR = "/mnt/data/services/silvasonic/status"


# --- Structlog Configuration ---
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("recorder")


class RecorderService:
    """Encapsulates the recording service logic."""

    def __init__(self) -> None:
        self.running: bool = False
        self.process: subprocess.Popen[bytes] | None = None
        self.monitor_thread: threading.Thread | None = None

        self.profile: MicrophoneProfile | None = None
        self.device: DetectedDevice | None = None
        self.strategy: typing.Any = (
            None  # typed as AudioStrategy but avoiding circular import issues if any
        )

        self.output_dir: str = ""
        self.udp_url: str = ""

        self._setup_logging()
        self._ensure_status_dir()

    def _setup_logging(self) -> None:
        """Configure logging for the recorder service."""
        log_dir = "/var/log/silvasonic"
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError:
            pass  # Ignore if we can't create it

        # Standard logging configuration that structlog will use
        # JSON output is handled by the structlog processor chain config above
        # But we need to ensure the handlers are plain Stream/File handlers
        # and structlog wraps them.

        # Actually, to get JSON output into the standard logging handlers (File & Stream),
        # we need to ensure the formatter for these handlers creates the JSON.
        # structlog.stdlib.ProcessorFormatter is the bridge.

        pre_chain: list[typing.Any] = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
        ]

        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=pre_chain,
        )

        handlers: list[logging.Handler] = []

        # Stdout
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        handlers.append(stream_handler)

        # File
        log_file = os.path.join(log_dir, "recorder.log")
        try:
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except Exception:
            # We use the raw print here because logger isn't fully set up?
            # Or use logger? Logger is safe.
            pass

        # Configure stdlib logging to use these handlers
        logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)

    def _ensure_status_dir(self) -> None:
        """Ensure the status directory exists."""
        try:
            os.makedirs(STATUS_DIR, exist_ok=True)
        except OSError:
            pass

    def initialize(self) -> bool:
        """Load profile and prepare implementation strategy."""
        logger.info("Initializing Recorder Service...")

        # 1. Load Profile
        self.profile, self.device = get_active_profile()

        if not self.profile:
            logger.critical("No profile found/matched. Cannot start.")
            # We must fail fast so orchestrator knows config is bad
            return False

        if not self.device:
            logger.critical("Profile found but no device matched (and no mock). Cannot start.")
            return False

        logger.info(f"Selected Profile: {self.profile.name}")
        logger.info(f"Selected Device: {self.device.description}")

        # 2. Create Strategy
        self.strategy = create_strategy_for_profile(self.profile, self.device)

        # 3. Determine Output Directory
        rec_id = os.getenv("RECORDER_ID")
        if rec_id:
            dir_name = rec_id
        elif self.profile.slug:
            dir_name = self.profile.slug
        else:
            dir_name = "default"

        self.output_dir = os.path.join(BASE_OUTPUT_DIR, dir_name)
        os.makedirs(self.output_dir, exist_ok=True)

        self.udp_url = f"udp://{LIVE_STREAM_TARGET}:{LIVE_STREAM_PORT}"

        return True

    def run(self) -> None:
        """Main blocking loop."""
        if not self.profile:
            if not self.initialize():
                return

        self.running = True
        self._write_status("Starting")

        logger.info("Recorder Service Started.")

        while self.running:
            logger.info("Launching FFmpeg...")
            try:
                self._start_ffmpeg()
                self._write_status("Recording")
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                self._write_status("Error: Startup Failed")
                time.sleep(5)
                continue

            # Monitor Loop
            try:
                while self.running and self.process and self.process.poll() is None:
                    self._write_status("Recording")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Monitor Loop Error: {e}")

            if not self.running:
                break

    def _write_status(self, status: str) -> None:
        """Write status using global handler."""
        write_status(status, self.profile, self.device)

    def _start_ffmpeg(self) -> None:
        """Start FFmpeg process using global handler."""
        if not self.profile or not self.device or not self.strategy:
            raise RuntimeError("Service not initialized or missing hardware.")

        self.process = start_recording(self.profile, self.device, self.output_dir, self.strategy)


# Global state for the main loop
running: bool = True
ffmpeg_process: subprocess.Popen[bytes] | None = None

# --- Status Caching ---
_last_status_write: float = 0
_last_status_hash: int = 0


def setup_logging() -> None:
    """Configure logging for the recorder service."""
    log_dir = "/var/log/silvasonic"
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        pass  # Ignore if we can't create it

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


def ensure_status_dir() -> None:
    """Ensure the status directory exists."""
    try:
        os.makedirs(STATUS_DIR, exist_ok=True)
    except OSError:
        pass


def write_status(
    status: str, profile: typing.Any = None, device: typing.Any = None, last_file: str | None = None
) -> None:
    """Write status to disk only if changed or interval elapsed (120s)."""
    global _last_status_write, _last_status_hash

    # 1. Build data object
    # Use .model_dump() for Pydantic models, fallback to asdict if needed or empty dict
    profile_data = profile.model_dump() if profile else {}
    device_data = device.model_dump() if device else {}

    data = {
        "service": "recorder",
        "timestamp": time.time(),
        "status": status,
        "cpu_percent": psutil.cpu_percent(),
        "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
        "meta": {
            "profile": profile_data,
            "device": device_data,
            "mode": "Continuous + Live Stream",
        },
        "pid": os.getpid(),
    }

    # 2. Check content hash (simple string hash of status + meta)
    # We exclude timestamp/cpu/mem from hash equality check to avoid jitter writing
    stable_content = f"{status}-{data['meta']}"
    current_hash = hash(stable_content)

    now = time.time()
    # Write if: Changed OR > 60s elapsed
    if current_hash != _last_status_hash or (now - _last_status_write) > 60:
        try:
            # Determine filename
            rec_id = os.getenv("RECORDER_ID")
            if rec_id:
                filename = f"recorder_{rec_id}.json"
            else:
                slug = "default"
                if profile and hasattr(profile, "slug"):
                    slug = profile.slug
                filename = f"recorder_{slug}.json"

            filepath = os.path.join(STATUS_DIR, filename)
            tmp_file = f"{filepath}.tmp"

            with open(tmp_file, "w") as f:
                json.dump(data, f)
            os.rename(tmp_file, filepath)

            _last_status_write = now
            _last_status_hash = current_hash

        except Exception as e:
            logger.error(f"Failed to write status: {e}")


def start_recording(
    profile: MicrophoneProfile, device: DetectedDevice, output_dir: str, strategy: typing.Any
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
        "-y",  # Overwrite if needed (mostly for pipe)
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

    # Signal Handlers
    def stop_service(sig: int, frame: typing.Any) -> None:
        global running
        logger.info("Stopping...")
        running = False
        if ffmpeg_process:
            try:
                ffmpeg_process.terminate()
                ffmpeg_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                ffmpeg_process.kill()
            except Exception:
                pass

    signal.signal(signal.SIGINT, stop_service)
    signal.signal(signal.SIGTERM, stop_service)

    write_status("Starting")

    while running:
        # Hardware Discovery / Re-Discovery Loop
        profile: MicrophoneProfile | None = None
        device: DetectedDevice | None = None
        strategy: typing.Any = (
            None  # typed as AudioStrategy but avoiding circular import issues if any
        )

        try:
            profile, device = get_active_profile()

            if not profile or not device:
                logger.warning("No audio device found. Retrying in 5s...")
                write_status("Hardware Search")
                time.sleep(5)
                continue

            logger.info(
                f"Active Profile: {profile.name} | Device: {device.description} ({device.hw_address})"
            )

            # Create Strategy
            strategy = create_strategy_for_profile(profile, device)

            # Output Dir
            rec_id = os.getenv("RECORDER_ID")
            dir_name = rec_id if rec_id else profile.slug
            output_dir = os.path.join(BASE_OUTPUT_DIR, dir_name)
            os.makedirs(output_dir, exist_ok=True)  # Ensure output dir exists

            logger.info("Launching FFmpeg...")
            proc = start_recording(profile, device, output_dir, strategy)
            ffmpeg_process = proc  # Update global reference
            write_status("Recording", profile, device)

            # Monitor Loop
            log_thread = threading.Thread(target=consume_stderr, args=(proc,), daemon=True)
            log_thread.start()

            while running and proc.poll() is None:
                write_status("Recording", profile, device)
                time.sleep(5)  # Just check-in sleep

            if not running:
                break

            logger.warning(f"FFmpeg exited with code {proc.returncode}. Hardware might be lost.")
            write_status("Error: Restarting", profile, device)

            # Clean up strategy resources
            if strategy:
                strategy.stop()

            # Short pause before re-discovery
            time.sleep(5)

        except Exception as e:
            logger.error(f"Main Loop Error: {e}")
            write_status("Error: Main Loop", profile, device)
            if strategy:
                strategy.stop()
            time.sleep(5)

    write_status("Stopped")


if __name__ == "__main__":
    main()
