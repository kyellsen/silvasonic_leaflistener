import socket
import sys
import time
import typing
from pathlib import Path

import numpy as np
import soundfile as sf

# Config matching LiveProcessor
HOST = "127.0.0.1"
PORT = 1234
SAMPLE_RATE = 48000
CHUNK_SIZE = 4096  # Samples per packet
CHANNELS = 1


def load_playlist(audio_dir: Path) -> list[Path]:
    """Load all .flac and .wav files from the directory."""
    files = list(audio_dir.glob("*.flac")) + list(audio_dir.glob("*.wav"))
    if not files:
        print(f"No .flac or .wav files found in {audio_dir}")
        return []
    print(f"Found {len(files)} tracks.")
    return sorted(files)


def process_track(file_path: Path) -> np.ndarray[typing.Any, typing.Any] | None:
    """Load and process an audio track for streaming."""
    print(f"Loading {file_path.name}...")
    try:
        data, samplerate = sf.read(file_path, dtype="float32")

        # Stereo to Mono
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)

        # Resample if needed (Basic Linear Interpolation)
        if samplerate != SAMPLE_RATE:
            print(f"Resampling from {samplerate} to {SAMPLE_RATE}...")
            duration = len(data) / samplerate
            new_length = int(duration * SAMPLE_RATE)
            data = np.interp(np.linspace(0, len(data), new_length), np.arange(len(data)), data)

        # Convert to Int16
        # Clip to -1.0 ... 1.0 then scale
        data = np.clip(data, -1.0, 1.0)
        audio_int16 = (data * 32767).astype(np.int16)

        return typing.cast(np.ndarray[typing.Any, typing.Any], audio_int16)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None


def stream_loop(audio_dir: Path) -> None:
    """Continuously stream audio files from the directory."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Target: {HOST}:{PORT}")
    print(f"Format: {SAMPLE_RATE}Hz, Mono, s16le, {CHUNK_SIZE} samples/pkt")
    print("-" * 40)

    while True:
        playlist = load_playlist(audio_dir)
        if not playlist:
            print("Waiting for files... (Retry in 5s)")
            time.sleep(5)
            continue

        # Shuffle or Sequential? User said "im Kreis", implying sequential or random loop.
        # "5 verschiedene... in Dauerschleife".

        for track_path in playlist:
            audio_data = process_track(track_path)
            if audio_data is None:
                continue

            total_chunks = len(audio_data) // CHUNK_SIZE
            print(
                f"Streaming {track_path.name} "
                f"({total_chunks} chunks, ~{total_chunks * CHUNK_SIZE / SAMPLE_RATE:.1f}s)"
            )

            # Streaming Loop
            for i in range(0, len(audio_data), CHUNK_SIZE):
                chunk = audio_data[i : i + CHUNK_SIZE]

                # Pad last chunk if needed
                if len(chunk) < CHUNK_SIZE:
                    chunk = np.pad(chunk, (0, CHUNK_SIZE - len(chunk)))

                # Send bytes
                sock.sendto(chunk.tobytes(), (HOST, PORT))

                # Pacing
                # Realtime pacing: Chunk duration = 4096 / 48000 = ~0.0853s
                # We should sleep a bit less to account for overhead,
                # but simple sleep is usually fine for Mock.
                time.sleep(CHUNK_SIZE / SAMPLE_RATE)

            # Small pause between tracks
            time.sleep(1.0)


if __name__ == "__main__":
    base_dir = Path(__file__).parent / "mock_audio"

    if len(sys.argv) > 1:
        base_dir = Path(sys.argv[1])

    if not base_dir.exists():
        base_dir.mkdir(parents=True)
        print(f"Created {base_dir}")
        print("Please put .flac files here!")

    try:
        stream_loop(base_dir)
    except KeyboardInterrupt:
        print("\nStopping stream.")
