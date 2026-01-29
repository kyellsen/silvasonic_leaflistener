import logging
import os

import librosa
import matplotlib
import numpy as np

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class Thumbnailer:
    def __init__(self) -> None:
        pass

    def generate(self, wav_path: str) -> str | None:
        """
        Generates a PNG spectrogram for the given wav_path.
        The PNG is saved in the same directory with .png extension.
        Returns the path to the PNG if successful, None otherwise.
        """
        if not os.path.exists(wav_path):
            logger.error(f"Thumbnailer: File not found {wav_path}")
            return None

        png_path = wav_path.replace(".wav", ".png")
        if os.path.exists(png_path):
            # Already exists
            return png_path

        try:
            # Load audio
            # sr=None preserves native sampling rate (384kHz)
            y, sr = librosa.load(wav_path, sr=None)

            # Generate Spectrogram
            # n_fft=2048, hop_length=512 are standard defaults, can be tuned for bats
            D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)

            plt.figure(figsize=(10, 4))
            librosa.display.specshow(D, sr=sr, x_axis="time", y_axis="hz")
            plt.colorbar(format="%+2.0f dB")
            plt.tight_layout()

            plt.savefig(png_path)
            plt.close()

            logger.info(f"Generated spectrogram for {os.path.basename(wav_path)}")
            return png_path

        except Exception as e:
            logger.error(f"Failed to generate spectrogram for {wav_path}: {e}")
            return None
