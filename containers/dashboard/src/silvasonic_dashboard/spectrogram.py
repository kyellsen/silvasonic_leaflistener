import logging
import os

import matplotlib

# Force headless backend before importing pyplot
matplotlib.use("Agg")
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger("SpectrogramGenerator")


def generate_spectrogram(audio_path: str, output_path: str) -> bool:
    """Generates a spectrogram PNG from an audio file.
    Returns True if successful, False otherwise.
    """
    try:
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return False

        # Limit to 60 seconds to avoid massive memory usage
        # SR=48000 matches the recorder default
        y, sr = librosa.load(audio_path, sr=48000, duration=60)

        # Compute Spectrogram
        s_db = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)

        # Generate Plot
        # clear any existing plots to avoid memory leaks
        plt.clf()
        plt.figure(figsize=(10, 4))
        librosa.display.specshow(s_db, sr=sr, x_axis="time", y_axis="hz")  # type: ignore[attr-defined]
        plt.colorbar(format="%+2.0f dB")
        plt.title("Spectrogram")
        plt.tight_layout()

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        plt.savefig(output_path)
        plt.close()
        return True
    except Exception as e:
        logger.error(f"Failed to generate spectrogram for {audio_path}: {e}")
        return False
