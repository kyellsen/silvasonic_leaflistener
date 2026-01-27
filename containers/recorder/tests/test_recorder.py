import unittest
from unittest.mock import MagicMock, patch

from silvasonic_recorder.main import RecorderService
from silvasonic_recorder.mic_profiles import (
    AudioConfig,
    DetectedDevice,
    MicrophoneProfile,
    RecordingConfig,
)


class TestRecorderService(unittest.TestCase):
    """Test the RecorderService class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.service = RecorderService()

        # Mock Profile
        self.profile = MicrophoneProfile(
            name="Test Profile",
            slug="test_profile",
            audio=AudioConfig(channels=1, sample_rate=48000, bit_depth=16, format="S16_LE"),
            recording=RecordingConfig(
                chunk_duration_seconds=30, output_format="flac", compression_level=5
            ),
        )

        # Mock Device
        self.device = DetectedDevice(
            card_id="0", hw_address="hw:0,0", description="Test Device", usb_id="1234:5678"
        )

        # Mock Strategy
        self.strategy = MagicMock()
        self.strategy.get_ffmpeg_input_args.return_value = ["-f", "alsa", "-test_arg"]
        self.strategy.get_input_source.return_value = "hw:0,0"

    @patch("silvasonic_recorder.main.get_active_profile")
    @patch("silvasonic_recorder.main.create_strategy_for_profile")
    @patch("silvasonic_recorder.main.os.makedirs")
    def test_initialize(
        self, mock_makedirs: MagicMock, mock_create_strat: MagicMock, mock_get_profile: MagicMock
    ) -> None:
        """Test initialization logic."""
        mock_get_profile.return_value = (self.profile, self.device)
        mock_create_strat.return_value = self.strategy

        success = self.service.initialize()

        self.assertTrue(success)
        self.assertEqual(self.service.profile, self.profile)
        self.assertEqual(self.service.device, self.device)
        self.assertEqual(self.service.strategy, self.strategy)
        self.assertIn("test_profile", self.service.output_dir)

    @patch("silvasonic_recorder.main.subprocess.Popen")
    @patch("silvasonic_recorder.main.get_active_profile")
    @patch("silvasonic_recorder.main.create_strategy_for_profile")
    def test_start_ffmpeg(
        self, mock_create_strat: MagicMock, mock_get_profile: MagicMock, mock_popen: MagicMock
    ) -> None:
        """Test that _start_ffmpeg calls FFmpeg correctly."""
        # Setup Service state manually or via init
        mock_get_profile.return_value = (self.profile, self.device)
        mock_create_strat.return_value = self.strategy

        self.service.initialize()

        process_mock = MagicMock()
        mock_popen.return_value = process_mock
        process_mock.stderr = MagicMock()

        # Call private method for testing
        self.service._start_ffmpeg()

        args, kwargs = mock_popen.call_args
        cmd = args[0]

        # validations
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-test_arg", cmd)
        self.assertIn("hw:0,0", cmd)
        self.assertIn("flac", cmd)

        self.strategy.start_background_tasks.assert_called_once_with(process_mock)


if __name__ == "__main__":
    unittest.main()
