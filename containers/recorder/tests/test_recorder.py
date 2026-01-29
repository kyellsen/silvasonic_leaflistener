import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from silvasonic_recorder.main import Recorder
from silvasonic_recorder.mic_profiles import (
    AudioConfig,
    DetectedDevice,
    MicrophoneProfile,
    RecordingConfig,
)


class TestRecorder(unittest.TestCase):
    """Test the Recorder class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Mock settings before instantiating Recorder
        self.settings_patcher = patch("silvasonic_recorder.main.settings")
        self.mock_settings = self.settings_patcher.start()
        self.mock_settings.AUDIO_OUTPUT_DIR = "/tmp/audio"
        self.mock_settings.LOG_DIR = "/tmp/logs"
        self.mock_settings.STATUS_DIR = "/tmp/status"
        self.mock_settings.RECORDER_ID = "test_rec"
        self.mock_settings.MOCK_HARDWARE = True
        self.mock_settings.AUDIO_PROFILE = None
        self.mock_settings.STRICT_HARDWARE_MATCH = False
        self.mock_settings.LIVE_STREAM_TARGET = "localhost"
        self.mock_settings.LIVE_STREAM_PORT = 8010

        with patch("silvasonic_recorder.main.os.makedirs"):
            self.recorder = Recorder()

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

    def tearDown(self) -> None:
        self.settings_patcher.stop()

    @patch("silvasonic_recorder.main.get_active_profile")
    def test_discover_hardware(self, mock_get_profile: MagicMock) -> None:
        """Test hardware discovery."""
        mock_get_profile.return_value = (self.profile, self.device)

        profile, device = self.recorder._discover_hardware()

        self.assertEqual(profile, self.profile)
        self.assertEqual(device, self.device)
        mock_get_profile.assert_called_once()

    @patch("silvasonic_recorder.main.subprocess.Popen")
    @patch("silvasonic_recorder.main.os.makedirs")
    def test_start_ffmpeg(
        self,
        mock_makedirs: MagicMock,
        mock_popen: MagicMock,
    ) -> None:
        """Test that _start_ffmpeg calls FFmpeg correctly."""
        process_mock = MagicMock()
        process_mock.poll.return_value = None  # Process running
        mock_popen.return_value = process_mock

        output_dir = Path("/tmp/audio/test_profile")

        # Act
        self.recorder._start_ffmpeg(self.profile, self.device, output_dir, self.strategy)

        # Assert
        args, kwargs = mock_popen.call_args
        cmd = args[0]

        # validations
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-test_arg", cmd)
        self.assertIn("-filter_complex", cmd)
        self.assertIn("[high]", cmd)
        self.assertIn("pcm_s16le", cmd)

        # Verify strategy tasks started
        self.strategy.start_background_tasks.assert_called_once_with(process_mock)


if __name__ == "__main__":
    unittest.main()
