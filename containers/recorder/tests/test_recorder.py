import typing
import unittest
from unittest.mock import MagicMock, patch

from silvasonic_recorder import main


class TestRecorder(unittest.TestCase):
    """Test the Recorder module."""

    def setUp(self) -> None:
        """Set up test fixtures."""

        # Mock profile
        self.profile = MagicMock()
        self.profile.audio.channels = 1
        self.profile.audio.sample_rate = 48000
        self.profile.recording.chunk_duration_seconds = 30
        self.profile.recording.compression_level = 5
        self.profile.is_mock = False
        self.profile.slug = "test_profile"

        self.device = MagicMock()
        self.device.hw_address = "hw:0,0"

        self.output_dir = "/tmp/test_rec"

        # Mock Strategy
        self.strategy = MagicMock()
        self.strategy.get_ffmpeg_input_args.return_value = ["-f", "alsa", "-test_arg"]
        self.strategy.get_input_source.return_value = "hw:0,0"

    @patch("silvasonic_recorder.main.subprocess.Popen")
    @patch("silvasonic_recorder.main.os.makedirs")
    def test_start_recording(self, mock_makedirs: typing.Any, mock_popen: typing.Any) -> None:
        """Test that start_recording calls FFmpeg with correct arguments from strategy."""
        process_mock = MagicMock()
        mock_popen.return_value = process_mock

        # Call the function
        main.start_recording(self.profile, self.device, self.output_dir, self.strategy)

        # Verify directory creation
        mock_makedirs.assert_called_with(self.output_dir, exist_ok=True)

        # Verify FFmpeg call
        args, kwargs = mock_popen.call_args
        cmd = args[0]

        # Check essential flags
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-test_arg", cmd)  # From strategy
        self.assertIn(self.device.hw_address, cmd)
        self.assertIn("flac", cmd)

        # Check background tasks call
        self.strategy.start_background_tasks.assert_called_once_with(process_mock)

    @patch("silvasonic_recorder.main.subprocess.Popen")
    @patch("silvasonic_recorder.main.os.makedirs")
    def test_start_recording_mock_strategy(
        self, mock_makedirs: typing.Any, mock_popen: typing.Any
    ) -> None:
        """Test with different strategy args."""

        self.strategy.get_ffmpeg_input_args.return_value = ["-f", "s16le", "-input_mock"]
        self.strategy.get_input_source.return_value = "pipe:0"

        main.start_recording(self.profile, self.device, self.output_dir, self.strategy)

        args, kwargs = mock_popen.call_args
        cmd = args[0]

        self.assertIn("-input_mock", cmd)
        self.assertIn("pipe:0", cmd)


if __name__ == "__main__":
    unittest.main()
