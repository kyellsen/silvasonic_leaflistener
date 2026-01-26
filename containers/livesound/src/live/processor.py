import asyncio
import logging
import socket
import threading
import typing
from dataclasses import dataclass

import librosa
import numpy as np

logger = logging.getLogger("LiveProcessor")


@dataclass
class StreamConfig:
    """Configuration for the audio stream processing."""

    host: str = "0.0.0.0"
    port: int = 1234
    sample_rate: int = 48000
    channels: int = 1
    # 4096 samples @ 48k = ~85ms latency chunks
    chunk_size: int = 4096
    fft_window: int = 2048
    hop_length: int = 512


class AudioIngestor:
    """Ingests audio from UDP stream and processes it for visualization."""

    def __init__(self, config: StreamConfig | None = None):
        """Initialize the AudioIngestor."""
        if config is None:
            config = StreamConfig()
        self.config = config
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.config.host, self.config.port))

        self.running = False
        self.thread: threading.Thread | None = None

        # Thread-safe integration with AsyncIO
        self.loop: asyncio.AbstractEventLoop | None = None

        # Listeners for different data types
        self._spectrogram_queues: set[asyncio.Queue[list[int]]] = set()
        self._audio_queues: set[asyncio.Queue[bytes]] = set()

        logger.info(f"AudioIngestor initialized on UDP {self.config.host}:{self.config.port}")

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start the ingestion thread."""
        self.loop = loop
        self.running = True
        self.thread = threading.Thread(target=self._ingest_loop, daemon=True)
        self.thread.start()
        logger.info("Audio ingestion started.")

    def stop(self) -> None:
        """Stop the ingestion thread."""
        self.running = False
        if self.sock:
            self.sock.close()

    async def subscribe_spectrogram(self) -> asyncio.Queue[list[int]]:
        """Subscribe to spectrogram updates."""
        q: asyncio.Queue[list[int]] = asyncio.Queue()
        self._spectrogram_queues.add(q)
        return q

    def unsubscribe_spectrogram(self, q: asyncio.Queue[list[int]]) -> None:
        """Unsubscribe from spectrogram updates."""
        if q in self._spectrogram_queues:
            self._spectrogram_queues.remove(q)

    async def subscribe_audio(self) -> asyncio.Queue[bytes]:
        """Subscribe to raw audio updates."""
        # Limit queue size to prevent memory explosion if client is slow
        q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)
        self._audio_queues.add(q)
        return q

    def unsubscribe_audio(self, q: asyncio.Queue[bytes]) -> None:
        """Unsubscribe from raw audio updates."""
        if q in self._audio_queues:
            self._audio_queues.remove(q)

    def _broadcast_safe(self, queues: set[asyncio.Queue[typing.Any]], data: typing.Any) -> None:
        """Helper to put data into queues from a thread safely."""
        if not self.loop or not self.running:
            return

        for q in list(queues):
            try:
                self.loop.call_soon_threadsafe(q.put_nowait, data)
            except asyncio.QueueFull:
                # Drop frames if client is too slow (Backpressure)
                pass
            except Exception:
                pass

    def _ingest_loop(self) -> None:
        buffer_size = self.config.chunk_size * 2 * 2  # Safety buffer

        # Buffer for FFT
        fft_buffer = np.zeros(0, dtype=np.float32)

        # Pre-calculate mel basis for performance
        mel_basis = librosa.filters.mel(
            sr=self.config.sample_rate,
            n_fft=self.config.fft_window,
            n_mels=128,
            fmin=100,
            fmax=14000,  # Birds range
        )

        while self.running:
            try:
                data, _ = self.sock.recvfrom(buffer_size)
                if not data:
                    continue

                # 1. Distribute Raw Audio (Bytes)
                self._broadcast_safe(self._audio_queues, data)

                # OPTIMIZATION: Skip processing if no one is watching the spectrogram
                if not self._spectrogram_queues:
                    if len(fft_buffer) > 0:
                        fft_buffer = np.zeros(0, dtype=np.float32)
                    continue

                # 2. Process Spectrogram
                # int16 -> float32
                audio_chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

                fft_buffer = np.concatenate((fft_buffer, audio_chunk))

                # Process if we have enough data
                if len(fft_buffer) >= self.config.fft_window:
                    # Compute STFT
                    # We only take the slice needed
                    y = fft_buffer[: self.config.fft_window]

                    # Short-Time Fourier Transform
                    # Calculate power spectrogram (amplitude squared)
                    stft_matrix = librosa.stft(
                        y, n_fft=self.config.fft_window, hop_length=self.config.hop_length
                    )
                    power_spectrogram = np.abs(stft_matrix) ** 2

                    # Mel Spectrogram
                    mel_spec = mel_basis.dot(power_spectrogram)

                    # Power to dB
                    log_mel_spec = librosa.power_to_db(mel_spec, ref=np.max)

                    # Normalize -80dB to 0dB -> 0 to 255
                    normalized_spec = np.clip((log_mel_spec + 80) * (255 / 80), 0, 255).astype(
                        np.uint8
                    )

                    # We take the mean across time columns if chunk produced multiple columns
                    # Or just send the last column.
                    # D shape: (1025, T)
                    # S shape: (128, T)

                    # Provide a flat list of the latest spectral frame
                    # Taking the mean of the frames in this chunk to represent "now"
                    if normalized_spec.shape[1] > 0:
                        frame = np.mean(normalized_spec, axis=1).astype(np.uint8)

                        # Pack simple JSON-friendly struct
                        payload = frame.tolist()
                        self._broadcast_safe(self._spectrogram_queues, payload)

                    # Slide buffer
                    # step = self.config.chunk_size  # Advance by what we consumed?
                    # Actually, for continuous stream integration, we should keep the overlap.
                    # But for simple live viz, just sliding window is okay.

                    # Keep tail
                    overlap = self.config.fft_window - self.config.hop_length
                    if len(fft_buffer) > overlap:
                        fft_buffer = fft_buffer[-overlap:]

            except Exception as e:
                if self.running:
                    logger.error(f"Ingest Error: {e}")


# Singleton
processor = AudioIngestor()
