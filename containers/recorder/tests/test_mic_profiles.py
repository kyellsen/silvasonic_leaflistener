import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from silvasonic_recorder.mic_profiles import (
    DetectedDevice,
    MicrophoneProfile,
    create_strategy_for_profile,
    find_matching_profile,
    get_active_profile,
    get_alsa_devices,
    load_profiles,
)
from silvasonic_recorder.strategies import AlsaStrategy, FileMockStrategy


class TestMicProfiles(unittest.TestCase):
    """Test the mic_profiles module."""

    def setUp(self):
        self.mock_profiles_dir = Path("/tmp/mock_profiles")
        self.sample_profile_yaml = """
name: "Test Mic"
slug: "test_mic"
manufacturer: "TestMaker"
audio:
  sample_rate: 44100
  channels: 1
recording:
  chunk_duration_seconds: 15
device_patterns:
  - "Test Device"
usb_ids:
  - "1234:5678"
"""

    @patch("silvasonic_recorder.mic_profiles.Path.glob")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_profiles(self, mock_file, mock_glob):
        """Test loading profiles from YAML."""
        # Setup mock file
        mock_file.side_effect = [mock_open(read_data=self.sample_profile_yaml).return_value]

        # Setup mock glob
        mock_path = MagicMock(spec=Path)
        mock_path.stem = "test_mic"
        mock_glob.return_value = [mock_path]

        profiles = load_profiles(self.mock_profiles_dir)

        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].name, "Test Mic")
        self.assertEqual(profiles[0].audio.sample_rate, 44100)
        self.assertEqual(profiles[0].slug, "test_mic")

    @patch("silvasonic_recorder.mic_profiles.subprocess.run")
    @patch("silvasonic_recorder.mic_profiles.Path")
    @patch("silvasonic_recorder.mic_profiles.os.path.exists")
    def test_get_alsa_devices(self, mock_exists, mock_path_cls, mock_subprocess):
        """Test ALSA device detection."""
        # Mock arecord -l output
        mock_subprocess.return_value.stdout = """
card 0: PCH [HDA Intel PCH], device 0: ALC257 Analog [ALC257 Analog]
card 1: UAC20 [UAC2.0 Capture], device 0: USB Audio [USB Audio]
"""
        mock_subprocess.return_value.stderr = ""

        # Mock /sys/class/sound checks for USB IDs
        # We need to simulate the iteration over /sys/class/sound/card*
        # This is tricky because it iterates using Path.glob.
        # Let's rely on the modalias or simply mock the dictionary logic if possible.
        # But the function is self-contained.

        # Simplified approach: Just check parsing of arecord output first
        # ignoring the complex USB ID resolution for now (or mocking it if needed)

        # We can simulate sys/class/sound/card1/device/idVendor exists
        mock_exists.return_value = True

        # Mock Path("/sys/class/sound").glob("card*")
        mock_sys_sound = MagicMock()
        mock_path_cls.return_value = mock_sys_sound  # /sys/class/sound

        # This part is hard to mock precisely without a lot of setup for Path.
        # Let's focus on the arecord parsing which is the critical part for device list

        devices = get_alsa_devices()

        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].card_id, "0")
        self.assertEqual(devices[0].hw_address, "plughw:0,0")
        self.assertIn("HDA Intel PCH", devices[0].description)

        self.assertEqual(devices[1].card_id, "1")
        self.assertEqual(devices[1].hw_address, "plughw:1,0")

    def test_find_matching_profile_strict_usb(self):
        """Test matching by USB ID."""
        # Note: Current implementation requires at least one pattern to enter the matching loop
        profile = MicrophoneProfile(name="Rode", usb_ids=["1234:5678"], device_patterns=["*"])
        device = DetectedDevice(
            card_id="1", hw_address="hw:1,0", description="Gen", usb_id="1234:5678"
        )

        match, dev = find_matching_profile(
            [profile], force_mock=False
        )  # supply devices? No, find_matching calls get_alsa_devices internally

        # We need to mock get_alsa_devices inside find_matching_profile
        with patch("silvasonic_recorder.mic_profiles.get_alsa_devices", return_value=[device]):
            match, dev = find_matching_profile([profile])
            self.assertEqual(match, profile)
            self.assertEqual(dev, device)

    def test_find_matching_profile_pattern(self):
        """Test matching by description pattern."""
        profile = MicrophoneProfile(name="Rode", device_patterns=["Rode NT"])
        device = DetectedDevice(
            card_id="1", hw_address="hw:1,0", description="Rode NT-USB", usb_id=None
        )

        with patch("silvasonic_recorder.mic_profiles.get_alsa_devices", return_value=[device]):
            match, dev = find_matching_profile([profile])
            self.assertEqual(match, profile)
            self.assertEqual(dev, device)

    def test_find_matching_profile_force_profile(self):
        """Test forced profile selection."""
        profile1 = MicrophoneProfile(name="Rode", slug="rode", device_patterns=["Rode"])
        profile2 = MicrophoneProfile(name="Other", slug="other", device_patterns=["Other"])

        device1 = DetectedDevice(card_id="1", hw_address="hw:1,0", description="Rode NT-USB")
        device2 = DetectedDevice(card_id="2", hw_address="hw:2,0", description="Other Mic")

        with patch(
            "silvasonic_recorder.mic_profiles.get_alsa_devices", return_value=[device1, device2]
        ):
            # Force "other"
            match, dev = find_matching_profile([profile1, profile2], force_profile="other")
            self.assertEqual(match, profile2)
            self.assertEqual(dev, device2)

    def test_find_matching_profile_mock_mode(self):
        """Test mock mode."""
        profiles = [MicrophoneProfile(name="Real", is_mock=False)]

        # Should create default mock
        match, dev = find_matching_profile(profiles, force_mock=True)
        self.assertTrue(match.is_mock)
        self.assertEqual(dev.card_id, "mock")

        # Should find existing mock profile
        mock_profile = MicrophoneProfile(name="MyMock", is_mock=True)
        match, dev = find_matching_profile([mock_profile], force_mock=True)
        self.assertEqual(match, mock_profile)

    def test_create_strategy_factory(self):
        """Test factory method for strategies."""
        # 1. Real
        real_profile = MicrophoneProfile(name="Real")
        real_device = DetectedDevice(card_id="0", hw_address="hw:0,0", description="Real")

        strategy = create_strategy_for_profile(real_profile, real_device)
        self.assertIsInstance(strategy, AlsaStrategy)
        self.assertEqual(strategy.hw_address, "hw:0,0")

        # 2. Mock
        mock_profile = MicrophoneProfile(name="Use File", is_mock=True)
        mock_device = DetectedDevice(card_id="mock", hw_address="mock", description="mock")

        with patch("silvasonic_recorder.mic_profiles.os.environ.get", return_value="/tmp/mock"):
            strategy = create_strategy_for_profile(mock_profile, mock_device)
            self.assertIsInstance(strategy, FileMockStrategy)
            self.assertEqual(strategy.watch_dir, Path("/tmp/mock"))

    @patch("silvasonic_recorder.mic_profiles.load_profiles")
    @patch("silvasonic_recorder.mic_profiles.find_matching_profile")
    def test_get_active_profile(self, mock_find, mock_load):
        """Test the main entry point."""
        mock_load.return_value = ["profiles"]
        mock_find.return_value = ("profile", "device")

        p, d = get_active_profile(mock_mode=True)

        mock_find.assert_called_with(
            ["profiles"], force_mock=True, force_profile=None, strict_mode=False
        )


if __name__ == "__main__":
    unittest.main()
