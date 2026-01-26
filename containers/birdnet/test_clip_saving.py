import csv
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Mock config and database before importing analyzer
sys.modules['src.database'] = MagicMock()
sys.modules['src.config'] = MagicMock()

from src.config import config
from src.database import db

# Setup Mock Config
config.RESULTS_DIR = Path("/tmp/birdnet_test_results")
config.CLIPS_DIR = config.RESULTS_DIR / "clips"
config.birdnet_settings = {
    'min_conf': 0.5, 'lat': 10, 'lon': 10, 'week': 1,
    'overlap': 0, 'sensitivity': 1, 'threads': 1
}
config.LATITUDE = 10
config.LONGITUDE = 10

# Now import analyzer
from src.analyzer import BirdNETAnalyzer


class TestClipSaving(unittest.TestCase):
    def setUp(self):
        # Setup directories
        if config.RESULTS_DIR.exists():
            shutil.rmtree(config.RESULTS_DIR)
        config.RESULTS_DIR.mkdir(parents=True)

        self.analyzer = BirdNETAnalyzer()

        # Create a dummy audio file
        self.test_audio = Path("/tmp/test_audio.wav")
        self.create_dummy_wav(self.test_audio)

    def tearDown(self):
        if config.RESULTS_DIR.exists():
             shutil.rmtree(config.RESULTS_DIR)
        if self.test_audio.exists():
            self.test_audio.unlink()

    def create_dummy_wav(self, path):
        import numpy as np
        import soundfile as sf
        sr = 48000
        duration = 5
        data = np.random.uniform(-1, 1, size=(sr * duration,))
        sf.write(str(path), data, sr)

    def create_dummy_csv(self, output_dir, filename):
        csv_path = Path(output_dir) / f"{filename}.BirdNET.results.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Start (s)', 'End (s)', 'Scientific name', 'Common name', 'Confidence'])
            writer.writerow(['1.0', '2.0', 'Turdus merula', 'Common Blackbird', '0.85'])
            writer.writerow(['3.0', '4.0', 'Erithacus rubecula', 'European Robin', '0.90'])
        return csv_path

    @patch('src.analyzer.BirdNETAnalyzer._trigger_alert')
    @patch('src.analyzer.bn_analyze')
    @patch('src.analyzer.BirdNETAnalyzer._run_ffmpeg_resampling')
    def test_clip_saving(self, mock_ffmpeg, mock_bn, mock_alert):
        # Setup Mocks
        def ffmpeg_side_effect(input_path, output_path):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(input_path, output_path)
            return True
        
        mock_ffmpeg.side_effect = ffmpeg_side_effect

        # Mock bn_analyze to write a CSV file to the output directory
        def side_effect(**kwargs):
            output_dir = kwargs.get('output')
            # Create a dummy CSV in that directory
            self.create_dummy_csv(output_dir, self.test_audio.stem + "_48k")

        mock_bn.side_effect = side_effect

        # Run process
        self.analyzer.process_file(str(self.test_audio))

        # Verify Clips
        clips = list(config.CLIPS_DIR.glob("*.wav"))
        self.assertEqual(len(clips), 2, "Should have saved 2 clips")

        # Verify filenames
        # {original_name}_{start}_{end}_{species}.wav
        # validation for Blackbird: 1.0 - 2.0
        # Analyzer adds _48k to the resampled filename used for clipping
        expected_1 = f"{self.test_audio.stem}_48k_1.0_2.0_Common_Blackbird.wav"
        clip_path = config.CLIPS_DIR / expected_1
        self.assertTrue(clip_path.exists(), f"Clip {expected_1} not found")

        # Verify Duration (padded)
        # Original: 1.0s. Padded: 3s + 1s + 3s = 7s.
        # But file is only 5s long.
        # Start: 1.0 - 3 = -2 -> 0
        # End: 2.0 + 3 = 5.0 -> 5.0
        # Result length: 5.0s
        import soundfile as sf
        info = sf.info(str(clip_path))
        # Allow small floating point tolerance, but with integer samples it should be exact for 48k?
        # Duration might be float.
        self.assertAlmostEqual(info.duration, 5.0, delta=0.1, msg="Clip should be padded to full file duration in this case")

        # Verify DB calls
        # We expect 2 save_detection calls
        self.assertEqual(db.save_detection.call_count, 2)

        # Check args of first call
        args, _ = db.save_detection.call_args_list[0]
        detection = args[0]
        self.assertEqual(detection['common_name'], 'Common Blackbird')
        self.assertIn('clip_path', detection)
        # We checked absolute path str is returned
        self.assertTrue(detection['clip_path'].endswith(expected_1))

if __name__ == '__main__':
    unittest.main()
