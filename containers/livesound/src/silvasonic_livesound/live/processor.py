import asyncio
import logging
import math
import socket
import threading
import typing
from dataclasses import dataclass

import librosa
import numpy as np
import orjson

from ..config import settings
from .models import SourceStatus

logger = logging.getLogger("LiveProcessor")


@dataclass
class StreamMetrics:
    packets_received: int = 0
    rms_db: float = -100.0


class AudioIngestor:
    """Ingests audio from multiple UDP streams and processes them for visualization."""

    def __init__(self) -> None:
        """Initialize the AudioIngestor."""
        # Sockets: {source_name: socket}
        self.sockets: dict[str, socket.socket] = {}
        # Port mapping: {source_name: port}
        self.source_ports: dict[str, int] = {}

        # Threads: {source_name: thread}
        self.threads: dict[str, threading.Thread] = {}
        # Metrics: {source_name: StreamMetrics}
        self.metrics: dict[str, StreamMetrics] = {}

        self._lock = threading.Lock()

        self.running = False

        # Thread-safe integration with AsyncIO
        self.loop: asyncio.AbstractEventLoop | None = None

        # Listeners: {source_name: set(queues)}
        self._spectrogram_queues: dict[str, set[asyncio.Queue[bytes]]] = {}
        self._audio_queues: dict[str, set[asyncio.Queue[bytes]]] = {}

        # Initialize sockets from static config (env vars)
        self.update_sources(settings.LISTEN_PORTS)

        logger.info("AudioIngestor initialized.")

    def update_sources(self, new_ports: dict[str, int]) -> None:
        """Update active sockets based on new mapping."""
        # 1. Add New
        for source, port in new_ports.items():
            if source not in self.sockets:
                self.add_source(source, port)

    def add_source(self, name: str, port: int) -> None:
        """Add a new audio source dynamically."""
        with self._lock:
            if name in self.sockets:
                logger.warning(f"Source {name} already exists.")
                return

            try:
                self._setup_socket(name, port)
                self.source_ports[name] = port
                self.metrics[name] = StreamMetrics()

                # Start thread if running
                if self.running and name in self.sockets:
                    self._start_ingestion_thread(name)
            except Exception as e:
                logger.error(f"Failed to add source {name}: {e}")

    def remove_source(self, name: str) -> None:
        """Remove a source dynamically."""
        # Optimistic removal
        sock = self.sockets.pop(name, None)
        self.source_ports.pop(name, None)
        self.metrics.pop(name, None)

        if sock:
            try:
                sock.close()
            except Exception:
                pass

        # Thread handles its own exit when socket is closed or recv fails
        logger.info(f"Removed source {name}")

    def get_source_stats(self) -> list[SourceStatus]:
        """Get snapshot of current source statistics."""
        stats = []
        with self._lock:
            for name, port in self.source_ports.items():
                m = self.metrics.get(name, StreamMetrics())
                active = name in self.threads and self.threads[name].is_alive()
                stats.append(
                    SourceStatus(
                        name=name,
                        port=port,
                        active=active,
                        rms_db=m.rms_db,
                        packets_received=m.packets_received,
                    )
                )
        return stats

    def _setup_socket(self, source: str, port: int) -> None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Allow reuse address to recover quickly
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((settings.HOST, port))
            self.sockets[source] = sock
            logger.info(f"Bound source '{source}' to UDP {settings.HOST}:{port}")
        except Exception as e:
            logger.error(f"Failed to bind source '{source}' on port {port}: {e}")
            raise

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start the ingestion threads."""
        self.loop = loop
        self.running = True

        # Start existing threads
        for source in list(self.sockets.keys()):
            self._start_ingestion_thread(source)

        logger.info("Audio ingestion threads started.")

    def _start_ingestion_thread(self, source: str) -> None:
        if source not in self.threads or not self.threads[source].is_alive():
            sock = self.sockets[source]
            t = threading.Thread(target=self._ingest_loop, args=(source, sock), daemon=True)
            self.threads[source] = t
            t.start()

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

    async def subscribe_spectrogram(self, source: str = "default") -> asyncio.Queue[bytes]:
        """Subscribe to spectrogram updates for a specific source."""
        # Use first available source if default requested but not present (fallback)
        if source == "default":
            if "default" not in self.sockets and self.sockets:
                source = next(iter(self.sockets))

        with self._lock:
            if source not in self._spectrogram_queues:
                self._spectrogram_queues.setdefault(source, set())

            q: asyncio.Queue[bytes] = asyncio.Queue()
            self._spectrogram_queues[source].add(q)

        return q

    def unsubscribe_spectrogram(self, q: asyncio.Queue[bytes], source: str = "default") -> None:
        """Unsubscribe from spectrogram updates."""
        with self._lock:
            # If we don't know the source, check all (expensive but safe) or require source
            if source in self._spectrogram_queues and q in self._spectrogram_queues[source]:
                self._spectrogram_queues[source].remove(q)
                return

            # Fallback cleanup
            for s in self._spectrogram_queues:
                if q in self._spectrogram_queues[s]:
                    self._spectrogram_queues[s].remove(q)

    async def subscribe_audio(self, source: str = "default") -> asyncio.Queue[bytes]:
        """Subscribe to raw audio updates."""
        if source == "default":
            if "default" not in self.sockets and self.sockets:
                source = next(iter(self.sockets))

        with self._lock:
            if source not in self._audio_queues:
                self._audio_queues.setdefault(source, set())

            # Limit queue size to prevent memory explosion if client is slow
            q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)
            self._audio_queues[source].add(q)
        return q

    def unsubscribe_audio(self, q: asyncio.Queue[bytes], source: str = "default") -> None:
        """Unsubscribe from raw audio updates."""
        with self._lock:
            if source in self._audio_queues and q in self._audio_queues[source]:
                self._audio_queues[source].remove(q)
                return

            for s in self._audio_queues:
                if q in self._audio_queues[s]:
                    self._audio_queues[s].remove(q)

    def _broadcast_safe(self, queues: set[asyncio.Queue[typing.Any]], data: typing.Any) -> None:
        """Helper to put data into queues from a thread safely."""
        if not self.loop or not self.running:
            return

        # Snapshot the queues under lock to avoid "Set changed size during iteration"
        with self._lock:
            if not queues:
                return
            target_queues = list(queues)

        for q in target_queues:
            try:
                self.loop.call_soon_threadsafe(q.put_nowait, data)
            except asyncio.QueueFull:
                # Drop frames if client is too slow (Backpressure)
                pass
            except Exception:
                pass

    def _ingest_loop(self, source: str, sock: socket.socket) -> None:
        buffer_size = settings.CHUNK_SIZE * 2 * 2  # Safety buffer

        # Pre-calculate mel basis for performance
        mel_basis = librosa.filters.mel(
            sr=settings.SAMPLE_RATE,
            n_fft=settings.FFT_WINDOW,
            n_mels=128,
            fmin=100,
            fmax=14000,  # Birds range
        )

        rb_size = settings.FFT_WINDOW + settings.CHUNK_SIZE
        ring_buffer = np.zeros(rb_size, dtype=np.float32)

        logger.info(f"Ingestion loop started for {source}")

        while self.running:
            try:
                data, _ = sock.recvfrom(buffer_size)
                if not data:
                    continue

                # --- 1. Update Metrics ---
                # We need a rough RMS estimate.
                # int16 -> float
                audio_chunk_int16 = np.frombuffer(data, dtype=np.int16)
                new_samples = audio_chunk_int16.astype(np.float32) / 32768.0

                rms = float(np.sqrt(np.mean(new_samples**2)))
                rms_db = 20 * math.log10(rms) if rms > 1e-9 else -100.0

                if source in self.metrics:
                    self.metrics[source].packets_received += 1
                    self.metrics[source].rms_db = round(rms_db, 1)

                # --- 2. Distribute Raw Audio (Bytes) ---
                if source in self._audio_queues:
                    self._broadcast_safe(self._audio_queues[source], data)

                # OPTIMIZATION: Skip processing if no one is watching the spectrogram
                if source not in self._spectrogram_queues or not self._spectrogram_queues[source]:
                    continue

                # --- 3. Process Spectrogram ---
                n_new = len(new_samples)

                # Shift left
                ring_buffer[:-n_new] = ring_buffer[n_new:]
                # Append new
                ring_buffer[-n_new:] = new_samples

                # Extract the analysis window (latest fft_window samples)
                y = ring_buffer[-settings.FFT_WINDOW :]

                # Compute STFT
                stft_matrix = librosa.stft(
                    y, n_fft=settings.FFT_WINDOW, hop_length=settings.HOP_LENGTH
                )
                power_spectrogram = np.abs(stft_matrix) ** 2

                # Mel Spectrogram
                mel_spec = mel_basis.dot(power_spectrogram)

                # Power to dB
                log_mel_spec = librosa.power_to_db(mel_spec, ref=np.max)

                # Normalize -80dB to 0dB -> 0 to 255
                normalized_spec = np.clip((log_mel_spec + 80) * (255 / 80), 0, 255).astype(np.uint8)

                # Provide a flat list of the latest spectral frame
                if normalized_spec.shape[1] > 0:
                    frame = np.mean(normalized_spec, axis=1).astype(np.uint8)
                    payload = orjson.dumps(frame, option=orjson.OPT_SERIALIZE_NUMPY)
                    self._broadcast_safe(self._spectrogram_queues[source], payload)

            except OSError:
                # Socket closed or similar
                if not self.running:
                    break
            except Exception as e:
                if self.running:
                    logger.error(f"Ingest Error [{source}]: {e}")


# Singleton
processor = AudioIngestor()
