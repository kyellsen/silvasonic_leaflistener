from unittest.mock import patch

import pytest
from silvasonic_controller.profiles_loader import (
    DetectedDevice,
    MicrophoneProfile,
    find_matching_profile,
    get_alsa_devices,
    load_profiles,
)

# Sample YAML content
SAMPLE_YAML = """
name: "Rode NT-USB"
manufacturer: "Rode"
model: "NT-USB"
device_patterns:
  - "Rode NT-USB"
audio:
  sample_rate: 48000
  channels: 2
recording:
  chunk_duration_seconds: 60
"""

SAMPLE_YAML_2 = """
name: "Generic USB"
priority: 100
device_patterns:
  - "USB Audio"
"""


@pytest.fixture
def mock_profiles_dir(tmp_path):
    d = tmp_path / "profiles"
    d.mkdir()
    (d / "rode.yml").write_text(SAMPLE_YAML)
    (d / "generic.yml").write_text(SAMPLE_YAML_2)
    return d


def test_profile_loading(mock_profiles_dir) -> None:
    profiles = load_profiles(mock_profiles_dir)
    assert len(profiles) == 2
    # Check sorting by priority (default 50 comes before 100)
    assert profiles[0].name == "Rode NT-USB"
    assert profiles[0].slug == "rode"  # Generated slug from filename
    assert profiles[1].name == "Generic USB"


def test_slug_generation() -> None:
    p = MicrophoneProfile(name="My  Cool Device!!!")
    p.__post_init__()
    assert p.slug == "my_cool_device"


def test_find_matching_profile_mock() -> None:
    profiles = [MicrophoneProfile(name="Test", is_mock=True)]
    profile, device = find_matching_profile(profiles, force_mock=True)
    assert profile.is_mock
    assert device.card_id == "mock"


def test_find_matching_profile_auto_match() -> None:
    profiles = [
        MicrophoneProfile(name="Rode", device_patterns=["Rode NT"]),
        MicrophoneProfile(name="Generic", device_patterns=["USB"]),
    ]

    mock_device = DetectedDevice(card_id="1", hw_address="hw:1,0", description="Rode NT-USB Audio")

    with patch(
        "silvasonic_controller.profiles_loader.get_alsa_devices", return_value=[mock_device]
    ):
        profile, device = find_matching_profile(profiles)
        assert profile.name == "Rode"
        assert device == mock_device


def test_find_matching_profile_fallback() -> None:
    profiles = [
        MicrophoneProfile(name="Specific", device_patterns=["Specific"]),
        MicrophoneProfile(name="Generic fallback", device_patterns=[]),
    ]

    mock_device = DetectedDevice(card_id="1", hw_address="hw:1,0", description="Unknown Device")

    with patch(
        "silvasonic_controller.profiles_loader.get_alsa_devices", return_value=[mock_device]
    ):
        profile, device = find_matching_profile(profiles)
        assert profile.name == "Generic fallback"


def test_find_matching_profile_forced() -> None:
    profiles = [MicrophoneProfile(name="Target", slug="target")]
    mock_device = DetectedDevice(card_id="1", hw_address="hw:1,0", description="Whatever")

    with patch(
        "silvasonic_controller.profiles_loader.get_alsa_devices", return_value=[mock_device]
    ):
        profile, device = find_matching_profile(profiles, force_profile="target")
        assert profile.name == "Target"
        assert device == mock_device


def test_find_matching_profile_no_devices() -> None:
    with patch("silvasonic_controller.profiles_loader.get_alsa_devices", return_value=[]):
        profile, device = find_matching_profile([])
        assert profile is None
        assert device is None


def test_real_scan_execution() -> None:
    # Test get_alsa_devices logic with mocked subprocess
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "card 1: Test [Test], device 0: Sub [Sub]"
        mock_run.return_value.stderr = ""
        devices = get_alsa_devices()
        assert len(devices) == 1
        assert devices[0].card_id == "1"


def test_real_scan_error() -> None:
    with patch("subprocess.run", side_effect=Exception("Boom")):
        devices = get_alsa_devices()
        assert devices == []


def test_load_profiles_not_exist(tmp_path) -> None:
    assert load_profiles(tmp_path / "nowhere") == []


def test_load_profiles_corrupt(mock_profiles_dir) -> None:
    (mock_profiles_dir / "bad.yml").write_text(":: :: invalid yaml")
    # Should skip bad file and load others
    profiles = load_profiles(mock_profiles_dir)
    assert len(profiles) == 2  # 2 good ones from fixture


def test_find_profile_forced_no_devices() -> None:
    # Forced profile but no devices available
    profiles = [MicrophoneProfile(name="Target", slug="target")]
    with patch("silvasonic_controller.profiles_loader.get_alsa_devices", return_value=[]):
        p, d = find_matching_profile(profiles, force_profile="target")
        assert p is None
        assert d is None


def test_generic_fallback_fail() -> None:
    # Profiles but no generic one
    profiles = [MicrophoneProfile(name="Specific", device_patterns=["Specific"])]
    mock_device = DetectedDevice(card_id="1", hw_address="hw:1,0", description="Unknown")

    with patch(
        "silvasonic_controller.profiles_loader.get_alsa_devices", return_value=[mock_device]
    ):
        p, d = find_matching_profile(profiles)
        assert p is None
        assert d is None
