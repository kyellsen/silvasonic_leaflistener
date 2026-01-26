import logging
import subprocess
import threading
import time
import typing
from abc import ABC, abstractmethod
from pathlib import Path

# Try importing soundfile/numpy, but don't crash if missing (though they should be installed)
try:
    import numpy as np
    import soundfile as sf
except ImportError:
    np = None
    sf = None

logger = logging.getLogger("recorder.strategies")


class AudioStrategy(ABC):
    """Abstract Base Class for Audio Acquisition Strategies."""

    @abstractmethod
    def get_ffmpeg_input_args(self) -> list[str]:
        """Return the FFmpeg input arguments (before -i)."""
        pass

    @abstractmethod
    def get_input_source(self) -> str:
        """Return the input source string (the value for -i)."""
        pass

    def start_background_tasks(self, process: subprocess.Popen) -> None:  # noqa: B027
        """Hook to start any background threads (e.g. file reading) after FFmpeg starts."""
        pass

    def stop(self) -> None:  # noqa: B027
        """Hook to clean up resources."""
        pass


class AlsaStrategy(AudioStrategy):
    """Strategy for capturing from an ALSA hardware device."""

    def __init__(self, hw_address: str, channels: int = 1, sample_rate: int = 48000):
        self.hw_address = hw_address
        self.channels = channels
        self.sample_rate = sample_rate

    def get_ffmpeg_input_args(self) -> list[str]:
        return ["-f", "alsa", "-ac", str(self.channels), "-ar", str(self.sample_rate)]

    def get_input_source(self) -> str:
        return self.hw_address


class FileMockStrategy(AudioStrategy):
    """Strategy for simulating audio by reading files from a directory and piping to FFmpeg."""

    def __init__(self, watch_dir: Path, sample_rate: int = 48000, chunk_size: int = 4096):
        self.watch_dir = watch_dir
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.running = False
        self.thread: threading.Thread | None = None
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        if np is None or sf is None:
            logger.error("numpy or soundfile not installed. FileMockStrategy will fail.")

    def get_ffmpeg_input_args(self) -> list[str]:
        # We accept raw s16le audio via stdin (pipe:0)
        return [
            "-f",
            "s16le",
            "-ac",
            "1",
            "-ar",
            str(self.sample_rate),
        ]

    def get_input_source(self) -> str:
        return "pipe:0"

    def start_background_tasks(self, process: subprocess.Popen) -> None:
        self.running = True
        self.thread = threading.Thread(target=self._stream_loop, args=(process,), daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _load_playlist(self) -> list[Path]:
        if not self.watch_dir.exists():
            try:
                self.watch_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            return []

        files = list(self.watch_dir.glob("*.flac")) + list(self.watch_dir.glob("*.wav"))
        return sorted(files)

    def _process_track(
        self, file_path: Path
    ) -> typing.Any:  # Return type np.ndarray but avoid import error in type hint
        if sf is None or np is None:
            return None

        try:
            data, samplerate = sf.read(str(file_path), dtype="float32")

            # Stereo to Mono
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            # Resample if needed
            if samplerate != self.sample_rate:
                duration = len(data) / samplerate
                new_length = int(duration * self.sample_rate)
                data = np.interp(np.linspace(0, len(data), new_length), np.arange(len(data)), data)

            # Convert to Int16
            data = np.clip(data, -1.0, 1.0)
            audio_int16 = (data * 32767).astype(np.int16)
            return audio_int16
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return None

    def _stream_loop(self, process: subprocess.Popen) -> None:
        logger.info(f"Starting File Mock Stream from {self.watch_dir}")

        if process.stdin is None:
            logger.error("FFmpeg stdin is None! Cannot stream mock audio.")
            return

        while self.running and process.poll() is None:
            playlist = self._load_playlist()

            if not playlist:
                # Generate silence if no files
                silence = np.zeros(self.sample_rate * 5, dtype=np.int16)  # 5 seconds of silence
                try:
                    process.stdin.write(silence.tobytes())
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    break
                time.sleep(5)
                continue

            for track_path in playlist:
                if not self.running or process.poll() is not None:
                    break

                audio_data = self._process_track(track_path)
                if audio_data is None:
                    continue

                logger.info(f"Injecting {track_path.name} into audio stream...")

                # Stream in chunks
                for i in range(0, len(audio_data), self.chunk_size):
                    if not self.running:
                        break

                    chunk = audio_data[i : i + self.chunk_size]

                    try:
                        process.stdin.write(chunk.tobytes())
                        # process.stdin.flush() # Flush might be too aggressive, let OS buffer a bit? No, for realtime, we rely on timing.
                    except (BrokenPipeError, OSError):
                        logger.info("FFmpeg Mock Pipe broken.")
                        return

                    # Realtime pacing
                    sleep_time = len(chunk) / self.sample_rate
                    # Sleep slightly less to keep pipe full?
                    # Actually, for mock injection, being slightly faster is usually fine as FFmpeg consumes at rate?
                    # No, for pipe input without -re, FFmpeg consumes as fast as possible unless we pace it.
                    # Wait, we are NOT using -re. So we MUST pace perfectly or FFmpeg will record 'too fast'.
                    # So we should sleep exact duration.
                    time.sleep(sleep_time)

            # Pause between playlist loops
            time.sleep(1.0)
