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
        # Limit to 60 seconds to avoid massive memory usage / huge images for long files
        try:
            # Try to load just 60 seconds. 
            # If this fails (e.g. seek error), do NOT convert to full load.
            y, sr = librosa.load(filepath, sr=48000, duration=60)
        except Exception as e:
            print(f"Spectrogram generation failed: {e}")
            return {
                "error": str(e)
            }
        
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
