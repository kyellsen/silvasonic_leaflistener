import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

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

    def start_background_tasks(self, process: "subprocess.Popen[bytes]") -> None:  # noqa: B027
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

    def __init__(self, watch_dir: Path, sample_rate: int = 48000):
        self.watch_dir = watch_dir
        self.sample_rate = sample_rate
        self.temp_playlist = Path("/tmp/recorder_playlist.txt")

    def _generate_playlist(self) -> bool:
        """Scan directory and create FFmpeg concat playlist.
        Returns:
            bool: True if playlist created validly, False if empty.
        """
        if not self.watch_dir.exists():
            try:
                self.watch_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        return False

    def get_ffmpeg_input_args(self) -> list[str]:
        return ["-f", "concat", "-safe", "0"]

    def get_input_source(self) -> str:
        return str(self.temp_playlist)


class PulseAudioStrategy(AudioStrategy):
    """Strategy for capturing from PulseAudio/PipeWire server."""

    def __init__(self, source_name: str = "default", channels: int = 1, sample_rate: int = 48000):
        self.source_name = source_name
        self.channels = channels
        self.sample_rate = sample_rate

    def get_ffmpeg_input_args(self) -> list[str]:
        # Using -f pulse.
        # Note: Container needs access to pulse socket.
        return [
            "-f",
            "pulse",
            "-ac",
            str(self.channels),
            "-ar",
            str(self.sample_rate),
            # Pulse input may need fragment size adjustments for latency,
            # but for recording default is usually fine.
        ]

    def get_input_source(self) -> str:
        return self.source_name
