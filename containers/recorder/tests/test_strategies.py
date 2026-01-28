import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from silvasonic_recorder.strategies import AlsaStrategy, FileMockStrategy


class TestStrategies(unittest.TestCase):
    """Test AudioStrategy implementations."""

    def test_alsa_strategy(self):
        """Test AlsaStrategy argument generation."""
        strategy = AlsaStrategy(hw_address="hw:0,0", channels=2, sample_rate=44100)

        args = strategy.get_ffmpeg_input_args()
        self.assertEqual(args, ["-f", "alsa", "-ac", "2", "-ar", "44100"])

        self.assertEqual(strategy.get_input_source(), "hw:0,0")

    def test_file_mock_strategy_args(self):
        """Test FileMockStrategy argument generation."""
        strategy = FileMockStrategy(watch_dir=Path("/tmp/mock"))

        args = strategy.get_ffmpeg_input_args()
        self.assertEqual(args, ["-f", "concat", "-safe", "0"])

        self.assertEqual(strategy.get_input_source(), "/tmp/recorder_playlist.txt")

    @patch("silvasonic_recorder.strategies.Path.exists")
    @patch("silvasonic_recorder.strategies.Path.mkdir")
    def test_file_mock_strategy_playlist_creation_dir_missing(self, mock_mkdir, mock_exists):
        """Test playlist generation handles missing directory."""
        mock_exists.return_value = False

        strategy = FileMockStrategy(watch_dir=Path("/tmp/missing"))
        result = strategy._generate_playlist()

        # Should try to create dir and return False (since empty/no files yet)
        mock_mkdir.assert_called()
        self.assertFalse(result)

    def test_file_mock_strategy_hooks(self):
        """Test abstract methods implementations (hooks)."""
        strategy = AlsaStrategy("hw:0")
        # Ensure they don't crash
        strategy.start_background_tasks(MagicMock())
        strategy.stop()

    def test_pulse_audio_strategy(self):
        """Test PulseAudioStrategy argument generation."""
        from silvasonic_recorder.strategies import PulseAudioStrategy

        strategy = PulseAudioStrategy(source_name="default", channels=1, sample_rate=48000)

        args = strategy.get_ffmpeg_input_args()
        self.assertEqual(args, ["-f", "pulse", "-ac", "1", "-ar", "48000"])
        self.assertEqual(strategy.get_input_source(), "default")


if __name__ == "__main__":
    unittest.main()
