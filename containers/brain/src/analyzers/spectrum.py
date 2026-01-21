import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path
from .base import BaseAnalyzer
from src.config import config

class SpectrogramAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "spectrum"

    def analyze(self, filepath: str):
        y, sr = librosa.load(filepath, sr=None)
        
        # Compute Spectrogram
        D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
        
        # Generate Plot
        plt.figure(figsize=(10, 4))
        librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='hz')
        plt.colorbar(format='%+2.0f dB')
        plt.title('Spectrogram')
        plt.tight_layout()
        
        # Save to artifacts dir
        filename = Path(filepath).name
        artifact_name = f"{filename}_spec.png"
        artifact_path = config.ARTIFACTS_DIR / artifact_name
        
        plt.savefig(artifact_path)
        plt.close()
        
        return {
            "spectrogram_path": str(artifact_path)
        }
