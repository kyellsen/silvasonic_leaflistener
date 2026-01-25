import librosa
import numpy as np
import soundfile as sf
from .base import BaseAnalyzer

class LoudnessAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "loudness"

    def analyze(self, filepath: str):
        # Calculate RMS using streaming to handle large files without OOM
        sum_squares = 0.0
        total_samples = 0
        
        # Use a reasonable block size (e.g., 65536 samples)
        # We process at native sample rate to avoid expensive resampling of large files
        try:
            with sf.SoundFile(filepath) as f:
                # Process in blocks
                for block in f.blocks(blocksize=65536, dtype='float32', always_2d=True):
                    # Mix to mono if necessary
                    if block.shape[1] > 1:
                        y = np.mean(block, axis=1)
                    else:
                        y = block.flatten()
                    
                    sum_squares += np.sum(y**2)
                    total_samples += len(y)
                    
            if total_samples == 0:
                mean_rms = 0.0
            else:
                mean_rms = float(np.sqrt(sum_squares / total_samples))
                
        except Exception as e:
            # Fallback for formats soundfile might struggle with, or if file is small enough
            print(f"Streaming failed ({e}), falling back to standard load")
            y, _ = librosa.load(filepath, sr=48000, mono=True)
            rms = librosa.feature.rms(y=y)[0]
            mean_rms = float(np.mean(rms))

        # Simple activity threshold (e.g. 0.005 is very quiet)
        # This needs calibration, but provides a relative metric.
        is_active = mean_rms > 0.005 
        
        return {
            "rms_loudness": mean_rms,
            "is_active": is_active
        }
