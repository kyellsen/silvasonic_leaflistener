import librosa
import numpy as np
from .base import BaseAnalyzer

class FrequencyAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "frequency"

    def analyze(self, filepath: str):
        y, sr = librosa.load(filepath, sr=None)
        
        # FFT
        fft = np.fft.fft(y)
        magnitudes = np.abs(fft)
        frequencies = np.fft.fftfreq(len(y), 1/sr)
        
        # Find peak (ignoring DC component at 0)
        # Filter for positive frequencies only
        pos_mask = frequencies > 20 # Ignore sub-20Hz rumble
        peak_freq = frequencies[pos_mask][np.argmax(magnitudes[pos_mask])]
        
        return {
            "peak_frequency_hz": float(abs(peak_freq))
        }
