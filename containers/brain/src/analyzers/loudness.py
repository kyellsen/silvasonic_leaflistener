import librosa
import numpy as np
from .base import BaseAnalyzer

class LoudnessAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "loudness"

    def analyze(self, filepath: str):
        # Load audio (mono)
        y, _ = librosa.load(filepath, sr=48000, mono=True)
        
        # Calculate RMS
        rms = librosa.feature.rms(y=y)[0]
        mean_rms = float(np.mean(rms))
        
        # Simple activity threshold (e.g. 0.005 is very quiet)
        # This needs calibration, but provides a relative metric.
        is_active = mean_rms > 0.005 
        
        return {
            "rms_loudness": mean_rms,
            "is_active": is_active
        }
