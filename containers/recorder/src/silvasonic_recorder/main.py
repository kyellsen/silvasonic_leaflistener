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
from pathlib import Path

import psutil
import redis
import structlog

from silvasonic_recorder.config import settings
from silvasonic_recorder.mic_profiles import (
    DetectedDevice,
    MicrophoneProfile,
    create_strategy_for_profile,
    get_active_profile,
)

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


def setup_logging() -> None:
    """Configure logging for the recorder service."""
    try:
        os.makedirs(settings.LOG_DIR, exist_ok=True)
    except OSError:
        pass  # Ignore if we can't create it

    # JSON Formatter for stdlib handlers
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
    log_file = os.path.join(settings.LOG_DIR, "recorder.log")
    try:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except Exception as e:
        # Fallback to printer if logger isn't ready
        print(f"Failed to setup file logging: {e}")

    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


class Recorder:
    """Core Recorder Service."""

    def __init__(self) -> None:
        self.running: bool = False
        self.process: subprocess.Popen[bytes] | None = None
        self.output_dir: Path = Path(settings.AUDIO_OUTPUT_DIR)

        # Status caching
        self._last_status_write: float = 0
        self._last_status_hash: int = 0

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        try:
            os.makedirs(settings.STATUS_DIR, exist_ok=True)
            os.makedirs(self.output_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directories: {e}")

    def run(self) -> None:
        """Main service loop."""
        self.running = True
        logger.info("Recorder Service Started", config=settings.model_dump())
        self._write_status("Starting")

        while self.running:
            # 1. Hardware Discovery
            profile, device = self._discover_hardware()

            if not profile or not device:
                logger.warning("No audio device found. Retrying in 5s...")
                self._write_status("Hardware Search")
                time.sleep(5)
                continue

            logger.info(
                "Hardware Selected",
                profile=profile.name,
                device=device.description,
                hw_address=device.hw_address,
            )

            # 2. Prepare Strategy and Paths
            strategy = create_strategy_for_profile(profile, device)

            # Determine specific output directory
            rec_id = settings.RECORDER_ID
            dir_name = rec_id if rec_id else profile.slug
            current_output_path = self.output_dir / dir_name
            os.makedirs(current_output_path, exist_ok=True)

            # 3. Start Recording
            try:
                self._start_ffmpeg(profile, device, current_output_path, strategy)
                self._write_status("Recording", profile, device)
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                self._write_status("Error: Startup Failed", profile, device)
                if strategy:
                    strategy.stop()
                time.sleep(5)
                continue

            # 4. Monitor Loop
            if self.process:
                # Start logging consumer thread
                log_thread = threading.Thread(
                    target=self._consume_stderr, args=(self.process,), daemon=True
                )
                log_thread.start()

                while self.running and self.process.poll() is None:
                    self._write_status("Recording", profile, device)
                    time.sleep(5)

            # 5. Handle Exit/Crash
            if not self.running:
                break

            return_code = self.process.returncode if self.process else -1
            logger.warning(f"FFmpeg exited unexpectedly. Code: {return_code}")

            self._write_status("Error: Restarting", profile, device)

            # Cleanup
            if strategy:
                strategy.stop()
            self.process = None

            time.sleep(5)

        self._write_status("Stopped")
        logger.info("Recorder Service Stopped")

    def _discover_hardware(self) -> tuple[MicrophoneProfile | None, DetectedDevice | None]:
        """Wrapper for get_active_profile using settings."""
        return typing.cast(
            tuple[MicrophoneProfile | None, DetectedDevice | None],
            get_active_profile(
                mock_mode=settings.MOCK_HARDWARE,
                force_profile=settings.AUDIO_PROFILE,
                strict_mode=settings.STRICT_HARDWARE_MATCH,
            ),
        )

    def _start_ffmpeg(
        self,
        profile: MicrophoneProfile,
        device: DetectedDevice,
        output_dir: Path,
        strategy: typing.Any,
    ) -> None:
        """Start the FFmpeg process with V2 Dual-Stream logic."""
        udp_url = f"udp://{settings.LIVE_STREAM_TARGET}:{settings.LIVE_STREAM_PORT}"

        # Paths
        high_res_dir = output_dir / "high_res"
        low_res_dir = output_dir / "low_res"
        os.makedirs(high_res_dir, exist_ok=True)
        os.makedirs(low_res_dir, exist_ok=True)

        pattern_high = high_res_dir / "%Y-%m-%d_%H-%M-%S.wav"
        pattern_low = low_res_dir / "%Y-%m-%d_%H-%M-%S.wav"

        input_args = strategy.get_ffmpeg_input_args()
        input_source = strategy.get_input_source()

        # Filter Complex:
        # [0:a] split=3 [high][low_src][stream_src];
        # [low_src] aresample=48000 [low];
        # [stream_src] aresample=48000 [stream]

        filter_complex = (
            "[0:a]split=3[high][low_src][stream_src];"
            "[low_src]aresample=48000[low];"
            "[stream_src]aresample=48000[stream]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            *input_args,
            "-i",
            input_source,
            "-filter_complex",
            filter_complex,
            # Output 1: High Res (Source Rate) - WAV
            "-map",
            "[high]",
            "-f",
            "segment",
            "-segment_time",
            str(profile.recording.chunk_duration_seconds),
            "-strftime",
            "1",
            "-c:a",
            "pcm_s16le",  # Or s24le/s32le depending on source? Keeping simple s16le for compatibility unless specified. s32le for 384k? Spec says "WAV".
            str(pattern_high),
            # Output 2: Low Res (48k) - WAV
            "-map",
            "[low]",
            "-f",
            "segment",
            "-segment_time",
            str(profile.recording.chunk_duration_seconds),
            "-strftime",
            "1",
            "-c:a",
            "pcm_s16le",
            str(pattern_low),
            # Output 3: Live Stream (48k) - UDP
            "-map",
            "[stream]",
            "-f",
            "s16le",
            "-ac",
            "1",
            "-ar",
            "48000",
            udp_url,
        ]

        logger.info(f"Starting FFmpeg V2: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
        )

        # Start strategy background tasks
        strategy.start_background_tasks(self.process)

        if self.process.poll() is not None:
            # Consume stderr to see why
            err = self.process.stderr.read() if self.process.stderr else b""
            logger.error(f"FFmpeg died: {err.decode('utf-8', errors='ignore')}")
            raise RuntimeError("FFmpeg died immediately.")

    def _consume_stderr(self, proc: subprocess.Popen[bytes]) -> None:
        """Reads stderr in a separate thread."""
        try:
            if proc.stderr is None:
                return
            for line in iter(proc.stderr.readline, b""):
                line_str = line.decode("utf-8", errors="replace").strip()
                if line_str:
                    logger.debug(f"[FFmpeg] {line_str}")
        except Exception as e:
            logger.error(f"Log consumer error: {e}")
        finally:
            # Only close if we are sure? subprocess closes it ideally.
            pass

    def _write_status(
        self,
        status: str,
        profile: MicrophoneProfile | None = None,
        device: DetectedDevice | None = None,
    ) -> None:
        """Write status to Redis with TTL."""
        try:
            # Lazy init Redis connection to handle potential startup race conditions
            if not hasattr(self, "_redis"):
                self._redis = redis.Redis(
                    host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=1
                )

            profile_data = profile.model_dump() if profile else {}
            device_data = device.model_dump() if device else {}

            payload = {
                "service": "recorder",
                "timestamp": time.time(),
                "status": status,
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "meta": {
                    "profile": profile_data,
                    "device": device_data,
                    "mode": "Continuous + Live Stream",
                    "recorder_id": settings.RECORDER_ID,
                },
                "pid": os.getpid(),
            }

            # Use Redis key 'status:recorder:<id>' or 'status:recorder:<slug>'
            if settings.RECORDER_ID:
                key = f"status:recorder:{settings.RECORDER_ID}"
            else:
                slug = profile.slug if profile else "default"
                key = f"status:recorder:{slug}"

            # Set with 10s TTL (Heartbeat)
            self._redis.setex(key, 10, json.dumps(payload))

            # Optional: Publish for real-time consumers
            self._redis.publish("status_updates", json.dumps({"event": "update", "key": key}))

        except Exception as e:
            # Log but don't crash main loop
            logger.warning(f"Failed to write status to Redis: {e}")

    def stop(self) -> None:
        """Stop the service gracefully."""
        self.running = False
        if self.process:
            logger.info("Terminating FFmpeg...")
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"Error stopping process: {e}")


def main() -> None:
    setup_logging()

    recorder = Recorder()

    def signal_handler(sig: int, frame: typing.Any) -> None:
        logger.info(f"Received signal {sig}, stopping...")
        recorder.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        recorder.run()
    except Exception as e:
        logger.critical(f"Fatal Service Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
