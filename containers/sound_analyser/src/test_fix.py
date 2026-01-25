import numpy as np
import soundfile as sf
import os
from analyzers.loudness import LoudnessAnalyzer
from analyzers.frequency import FrequencyAnalyzer
from analyzers.spectrum import SpectrogramAnalyzer

def create_dummy_file(filename, duration=5, sr=48000):
    t = np.linspace(0, duration, int(sr*duration))
    # Create valid stereo audio
    y = np.sin(2 * np.pi * 440 * t)
    y = np.vstack([y, y]).T
    sf.write(filename, y, sr)
    print(f"Created dummy file: {filename}")

def test_analyzers():
    filename = "test_audio.wav"
    try:
        create_dummy_file(filename)
        
        print("\n--- Testing LoudnessAnalyzer ---")
        l_analyzer = LoudnessAnalyzer()
        res_l = l_analyzer.analyze(filename)
        print(f"Loudness result: {res_l}")
        
        print("\n--- Testing FrequencyAnalyzer ---")
        f_analyzer = FrequencyAnalyzer()
        res_f = f_analyzer.analyze(filename)
        print(f"Frequency result: {res_f}")
        
        print("\n--- Testing SpectrogramAnalyzer ---")
        s_analyzer = SpectrogramAnalyzer()
        # Mock artifacts dir since config might rely on it
        import sys
        from unittest.mock import MagicMock
        # We need to mock config because it expects ARTIFACTS_DIR
        # But wait, we are importing analyzers which import base which import config.
        # We might encounter import errors if dependencies are missing or config is broken.
        
        # Let's hope it runs.
        res_s = s_analyzer.analyze(filename)
        print(f"Spectrum result: {res_s}")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(filename):
            os.remove(filename)
            print("Cleaned up.")

if __name__ == "__main__":
    test_analyzers()
