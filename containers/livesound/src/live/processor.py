import asyncio
import logging
import socket
import threading
import typing
import os
from dataclasses import dataclass, field

import librosa
import numpy as np

logger = logging.getLogger("LiveProcessor")


@dataclass
class StreamConfig:
    """Configuration for the audio stream processing."""

    host: str = "0.0.0.0"
    # Mapping of Source Name -> Port
    # e.g. {"front": 1234, "back": 1235}
    ports: dict[str, int] = field(default_factory=dict)
    sample_rate: int = 48000
    channels: int = 1

    def __post_init__(self) -> None:
        """Parse LISTEN_PORTS env var if ports not provided."""
        if not self.ports:
            env_ports = os.getenv("LISTEN_PORTS", "")
            if env_ports:
                # Format: "front:1234,back:1235"
                try:
                    for part in env_ports.split(","):
                        name, port = part.split(":")
                        self.ports[name.strip()] = int(port.strip())
                except ValueError:
                    logger.error(f"Invalid LISTEN_PORTS format: {env_ports}. Fallback to default.")
            
            if not self.ports:
                # Default fallback
                self.ports = {"default": 1234}
    # 4096 samples @ 48k = ~85ms latency chunks
    chunk_size: int = 4096
    fft_window: int = 2048
    hop_length: int = 512


class AudioIngestor:
    """Ingests audio from multiple UDP streams and processes them for visualization."""

    def __init__(self, config: StreamConfig | None = None):
        """Initialize the AudioIngestor."""
        if config is None:
            config = StreamConfig()
        self.config = config
        
        # Sockets: {source_name: socket}
        self.sockets: dict[str, socket.socket] = {}
        
        # Threads: {source_name: thread}
        self.threads: dict[str, threading.Thread] = {}

        self.running = False
        self.status_dir = "/mnt/data/services/silvasonic/status"
        
        # Thread-safe integration with AsyncIO
        self.loop: asyncio.AbstractEventLoop | None = None

        # Listeners: {source_name: set(queues)}
        self._spectrogram_queues: dict[str, set[asyncio.Queue[list[int]]]] = {}
        self._audio_queues: dict[str, set[asyncio.Queue[bytes]]] = {}

        # Initialize sockets from static config (env vars)
        self.update_sources(self.config.ports)

        logger.info(f"AudioIngestor initialized.")

    def update_sources(self, new_ports: dict[str, int]) -> None:
        """Update active sockets based on new mapping."""
        # 1. Add New
        for source, port in new_ports.items():
            if source not in self.sockets:
                try:
                    self._setup_socket(source, port)
                    # Start thread if running
                    if self.running and source in self.sockets:
                        t = threading.Thread(target=self._ingest_loop, args=(source, self.sockets[source]), daemon=True)
                        self.threads[source] = t
                        t.start()
                except Exception as e:
                    logger.error(f"Failed to add source {source}: {e}")

        # 2. Remove Old (Optional - closing sockets might be safer than leaving them)
        # For now, we accumulate. Closing running threads is tricky without signaling.
        # But we can try.
        # If a port moves? (Unlikely)
        pass

    def _setup_socket(self, source: str, port: int) -> None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Allow reuse address to recover quickly
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.config.host, port))
            self.sockets[source] = sock
            logger.info(f"Bound source '{source}' to UDP {self.config.host}:{port}")
        except Exception as e:
            logger.error(f"Failed to bind source '{source}' on port {port}: {e}")

    def _watch_config_loop(self) -> None:
        """Poll for dynamic source configuration."""
        import json
        import time
        config_file = os.path.join(self.status_dir, "livesound_sources.json")
        last_mtime = 0

        while self.running:
            try:
                if os.path.exists(config_file):
                    mtime = os.path.getmtime(config_file)
                    if mtime > last_mtime:
                        last_mtime = mtime
                        with open(config_file) as f:
                            sources = json.load(f)
                            if isinstance(sources, dict):
                                self.update_sources(sources)
            except Exception as e:
                logger.error(f"Config Watch Error: {e}")
            
            time.sleep(2)

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start the ingestion threads."""
        self.loop = loop
        self.running = True
        
        # Start existing threads
        for source, sock in self.sockets.items():
            if source not in self.threads or not self.threads[source].is_alive():
                t = threading.Thread(target=self._ingest_loop, args=(source, sock), daemon=True)
                self.threads[source] = t
                t.start()
        
        # Start Config Watcher
        self.watcher_thread = threading.Thread(target=self._watch_config_loop, daemon=True)
        self.watcher_thread.start()
            
        logger.info("Audio ingestion threads started.")

    def stop(self) -> None:
        """Stop the ingestion threads."""
        self.running = False
        for sock in self.sockets.values():
            try:
                sock.close()
            except Exception:
                pass
        self.sockets.clear()
        # Threads will exit when sock.recv returns empty or error

    async def subscribe_spectrogram(self, source: str = "default") -> asyncio.Queue[list[int]]:
        """Subscribe to spectrogram updates for a specific source."""
        # Use first available source if default requested but not present (fallback)
        if source == "default" and "default" not in self._spectrogram_queues and self._spectrogram_queues:
            source = next(iter(self._spectrogram_queues))

        if source not in self._spectrogram_queues:
             logger.warning(f"Subscribe request for unknown source: {source}")
             # Return empty queue that will never get data? Or raise?
             # Better to register it conceptually or just fail softly.
             # Let's create an empty set to avoid crashes, but no data will come.
             self._spectrogram_queues.setdefault(source, set())

        q: asyncio.Queue[list[int]] = asyncio.Queue()
        self._spectrogram_queues[source].add(q)
        return q

    def unsubscribe_spectrogram(self, q: asyncio.Queue[list[int]], source: str = "default") -> None:
        """Unsubscribe from spectrogram updates."""
        # If we don't know the source, check all (expensive but safe) or require source
        # Ideally caller knows source.
        if source in self._spectrogram_queues and q in self._spectrogram_queues[source]:
            self._spectrogram_queues[source].remove(q)
            return

        # Fallback cleanup
        for s in self._spectrogram_queues:
            if q in self._spectrogram_queues[s]:
                self._spectrogram_queues[s].remove(q)

    async def subscribe_audio(self, source: str = "default") -> asyncio.Queue[bytes]:
        """Subscribe to raw audio updates."""
        if source == "default" and "default" not in self._audio_queues and self._audio_queues:
            source = next(iter(self._audio_queues))

        if source not in self._audio_queues:
             self._audio_queues.setdefault(source, set())

        # Limit queue size to prevent memory explosion if client is slow
        q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)
        self._audio_queues[source].add(q)
        return q

    def unsubscribe_audio(self, q: asyncio.Queue[bytes], source: str = "default") -> None:
        """Unsubscribe from raw audio updates."""
        if source in self._audio_queues and q in self._audio_queues[source]:
            self._audio_queues[source].remove(q)
            return

        for s in self._audio_queues:
            if q in self._audio_queues[s]:
                self._audio_queues[s].remove(q)

    def _broadcast_safe(self, queues: set[asyncio.Queue[typing.Any]], data: typing.Any) -> None:
        """Helper to put data into queues from a thread safely."""
        if not self.loop or not self.running or not queues:
            return

        for q in list(queues):
            try:
                self.loop.call_soon_threadsafe(q.put_nowait, data)
            except asyncio.QueueFull:
                # Drop frames if client is too slow (Backpressure)
                pass
            except Exception:
                pass

    def _ingest_loop(self, source: str, sock: socket.socket) -> None:
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

        logger.info(f"Ingestion loop started for {source}")

        while self.running:
            try:
                data, _ = sock.recvfrom(buffer_size)
                if not data:
                    continue

                # 1. Distribute Raw Audio (Bytes)
                if source in self._audio_queues:
                     self._broadcast_safe(self._audio_queues[source], data)

                # OPTIMIZATION: Skip processing if no one is watching the spectrogram
                if source not in self._spectrogram_queues or not self._spectrogram_queues[source]:
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
                        self._broadcast_safe(self._spectrogram_queues[source], payload)

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
                    logger.error(f"Ingest Error [{source}]: {e}")


# Singleton
# We can initialize with default config, but main.py might override it
# For now, let's allow it to be configured via Env in main.py
processor = AudioIngestor()
