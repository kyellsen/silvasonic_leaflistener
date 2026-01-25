import librosa
import numpy as np
import soundfile as sf
from .base import BaseAnalyzer

class FrequencyAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "frequency"

    def analyze(self, filepath: str):
        # Use streaming to find peak frequency (Average Magnitude Spectrum)
        # This avoids loading the whole file for one massive FFT
        
        n_fft = 65536 # High resolution for lower streams, decent for uniform processing
        accum_mag = np.zeros(n_fft // 2 + 1)
        block_count = 0
        sr = 48000 # Default/Fallback
        
        try:
            with sf.SoundFile(filepath) as f:
                sr = f.samplerate
                
                # Check consistency if we need specific SR, but usually native is fine for Peak Freq detecting
                # We use overlap=0 for speed/simplicity in this stats check
                
                # Check consistency if we need specific SR, but usually native is fine for Peak Freq detecting
                # We use overlap=0 for speed/simplicity in this stats check
                
                while True:
                    block = f.read(frames=n_fft, dtype='float32', always_2d=True)
                    
                    if len(block) == 0:
                        break

                    if len(block) < n_fft:
                        # Zero pad last block
                        pad_width = ((0, n_fft - len(block)), (0, 0))
                        block = np.pad(block, pad_width, mode='constant')
                        
                    # Mono
                    if block.shape[1] > 1:
                        y = np.mean(block, axis=1)
                    else:
                        y = block.flatten()
                        
                    # RFFT (Real FFT) - more efficient, returns n_fft//2 + 1 bins
                    mag = np.abs(np.fft.rfft(y))
                    accum_mag += mag
                    block_count += 1
            
            if block_count > 0:
                avg_mag = accum_mag / block_count
            else:
                avg_mag = accum_mag
                
            # Frequencies for RFFT
            frequencies = np.fft.rfftfreq(n_fft, 1/sr)
            
        except Exception as e:
            # Fallback
            print(f"Streaming frequency analysis failed: {e}")
            # Do NOT fallback to loading the entire file as it causes OOM on large high-res files
            # Return safe default
            return {
                "peak_frequency_hz": 0.0,
                "error": str(e)
            }

        # Find peak
        pos_mask = frequencies > 20 # Ignore sub-20Hz rumble
        
        # Handle case where all freq < 20 (unlikely)
        if not np.any(pos_mask):
            peak_freq = 0.0
        else:
            # Filter magnitudes
            valid_mags = avg_mag[pos_mask]
            valid_freqs = frequencies[pos_mask]
            peak_freq = valid_freqs[np.argmax(valid_mags)]
        
        return {
            "peak_frequency_hz": float(abs(peak_freq))
        }
