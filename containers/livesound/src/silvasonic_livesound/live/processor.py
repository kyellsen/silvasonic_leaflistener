import asyncio
import logging
import os
import socket
import threading
import typing

import librosa
import numpy as np
import orjson

from ..config import settings

logger = logging.getLogger("LiveProcessor")


class AudioIngestor:
    """Ingests audio from multiple UDP streams and processes them for visualization."""

    def __init__(self):
        """Initialize the AudioIngestor."""
        # Sockets: {source_name: socket}
        self.sockets: dict[str, socket.socket] = {}

        # Threads: {source_name: thread}
        self.threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

        self.running = False
        self.status_dir = "/mnt/data/services/silvasonic/status"

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
                try:
                    self._setup_socket(source, port)
                    # Start thread if running
                    if self.running and source in self.sockets:
                        t = threading.Thread(
                            target=self._ingest_loop,
                            args=(source, self.sockets[source]),
                            daemon=True,
                        )
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
            sock.bind((settings.HOST, port))
            self.sockets[source] = sock
            logger.info(f"Bound source '{source}' to UDP {settings.HOST}:{port}")
        except Exception as e:
            logger.error(f"Failed to bind source '{source}' on port {port}: {e}")

    def _watch_config_loop(self) -> None:
        """Poll for dynamic source configuration."""
        import json
        import time

        config_file = os.path.join(os.path.dirname(settings.STATUS_FILE), "livesound_sources.json")
        last_mtime: float = 0.0

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

    async def subscribe_spectrogram(self, source: str = "default") -> asyncio.Queue[bytes]:
        """Subscribe to spectrogram updates for a specific source."""
        # Use first available source if default requested but not present (fallback)
        if source == "default":
            if "default" not in self.sockets and self.sockets:
                source = next(iter(self.sockets))

        # Validate against ACTUAL hardware sockets, not queue dict
        if source not in self.sockets:
            logger.warning(f"Subscribe request for known source: {source}")
            # We can still register it, but it won't get data.
            # Alternatively, we could auto-create a socket if we were truly dynamic,
            # but here we just safely register the queue.

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

        # --- Ring Buffer Optimization ---
        # We need a buffer large enough to hold [Historical Data + New Chunk]
        # We need at least fft_window samples to compute one frame.
        # But we really want to process a stream.
        # To avoid np.concatenate, we allocate a fixed size buffer.
        # Size = fft_window + chunk_size (max new data)
        # Actually, we just need a rolling window of size fft_window.
        # But since we receive chunk_size data, we need room to shift.

        # ring_buffer holds the latest audio samples used for FFT
        # Initial capacity: Enough to hold the FFT window.
        # But wait, audio_chunk can be up to chunk_size (4096).
        # We want to perform FFT on the *last* fft_window (2048) samples
        # AFTER appending the new chunk.

        # Strategy:
        # 1. Keep a persistent buffer of size (fft_window + chunk_size).
        # 2. On new data (len=N):
        #    - Shift existing data left by N: buffer[:-N] = buffer[N:]
        #    - Insert new data at end: buffer[-N:] = new_data
        #    - Slice the last fft_window samples for processing: buffer[-fft_window:]

        rb_size = settings.FFT_WINDOW + settings.CHUNK_SIZE
        ring_buffer = np.zeros(rb_size, dtype=np.float32)

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
                    continue

                # 2. Process Spectrogram
                # int16 -> float32
                # We assume 16-bit PCM input
                audio_chunk_int16 = np.frombuffer(data, dtype=np.int16)

                # Normalize to -1.0 .. 1.0
                new_samples = audio_chunk_int16.astype(np.float32) / 32768.0

                n_new = len(new_samples)

                # --- Ring Buffer Logic ---
                # Shift left
                ring_buffer[:-n_new] = ring_buffer[n_new:]
                # Append new
                ring_buffer[-n_new:] = new_samples

                # Extract the analysis window (latest fft_window samples)
                y = ring_buffer[-settings.FFT_WINDOW :]

                # Compute STFT
                # Calculate power spectrogram (amplitude squared)
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
                # Taking the mean of the frames in this chunk to represent "now"
                if normalized_spec.shape[1] > 0:
                    frame = np.mean(normalized_spec, axis=1).astype(np.uint8)

                    # --- Performance Boost: orjson ---
                    # Pack simple JSON-friendly struct directly to bytes
                    # orjson can serialize numpy arrays natively via OPT_SERIALIZE_NUMPY
                    payload = orjson.dumps(frame, option=orjson.OPT_SERIALIZE_NUMPY)
                    self._broadcast_safe(self._spectrogram_queues[source], payload)

            except Exception as e:
                if self.running:
                    logger.error(f"Ingest Error [{source}]: {e}")


# Singleton
# We can initialize with default config, but main.py might override it
# For now, let's allow it to be configured via Env in main.py
processor = AudioIngestor()
